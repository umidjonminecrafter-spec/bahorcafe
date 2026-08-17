from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from decimal import Decimal
import logging

from .models import Table, TablePart, TableLayout, ProductCategory, Product, ProductIngredient
from apps.kitchen.models import Department
from apps.core.excel_importer import extract_rows_from_request, normalize_row_dict

logger = logging.getLogger('bahor_app')
from .serializers import (
    TableSerializer,
    TablePartSerializer,
    TableLayoutSerializer,
    ProductCategorySerializer,
    ProductSerializer,
    ProductIngredientSerializer
)

class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all().prefetch_related('parts')
    serializer_class = TableSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['branch', 'status', 'is_busy', 'is_active']
    search_fields = ['name']
    ordering_fields = ['id', 'name', 'table_number']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

class TablePartViewSet(viewsets.ModelViewSet):
    queryset = TablePart.objects.all()
    serializer_class = TablePartSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['table', 'is_active']

class TableLayoutView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        branch_id = request.query_params.get('branch_id') or request.query_params.get('branch')
        if branch_id:
            layout = TableLayout.objects.filter(branch_id=branch_id).first()
        else:
            layout = TableLayout.objects.first()

        if not layout:
            layout = TableLayout.objects.create(layout_data={})
        
        serializer = TableLayoutSerializer(layout)
        return Response(serializer.data)

    def post(self, request):
        branch_id = request.data.get('branch') or request.data.get('branch_id')
        layout_data = request.data.get('layout_data', request.data)
        
        layout = None
        if branch_id:
            layout = TableLayout.objects.filter(branch_id=branch_id).first()
        if not layout:
            layout = TableLayout.objects.first()
        if not layout:
            layout = TableLayout.objects.create(branch_id=branch_id, layout_data=layout_data)
        else:
            layout.layout_data = layout_data
            layout.save()

        serializer = TableLayoutSerializer(layout)
        return Response(serializer.data)

class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [AllowAny]
    search_fields = ['name']
    ordering_fields = ['order', 'id', 'name']

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category', 'department').prefetch_related('ingredients', 'ingredients__maxsulot')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category', 'department', 'is_active', 'is_weight_recipe']
    search_fields = ['name', 'mxik']
    ordering_fields = ['id', 'name', 'price', 'created_at']

class ProductIngredientViewSet(viewsets.ModelViewSet):
    queryset = ProductIngredient.objects.all().select_related('product', 'maxsulot')
    serializer_class = ProductIngredientSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['product', 'maxsulot']

class ExcelMenuImportView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @transaction.atomic
    def post(self, request):
        rows = extract_rows_from_request(request)
        if not rows:
            return Response({
                "status": "error",
                "message": "Fayl bo'sh yoki menyu taomlari topilmadi. Excel (.xlsx), CSV yoki JSON fayl yuboring.",
                "imported_rows": 0
            }, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []
        imported_items = []

        for idx, r in enumerate(rows, start=1):
            try:
                norm = normalize_row_dict(r)
                name = norm['name']
                if not name:
                    errors.append(f"{idx}-qator: Taom nomi bo'sh, o'tkazib yuborildi.")
                    continue

                # Resolve Category
                cat_name = norm['category']
                category = None
                if cat_name:
                    category, _ = ProductCategory.objects.get_or_create(name=cat_name)

                # Resolve Department
                dept_name = norm['department']
                department = None
                if dept_name:
                    department, _ = Department.objects.get_or_create(name=dept_name)

                price = norm['selling_price']
                cost_price = norm['purchase_price']
                markup = norm['margin_percent']
                unit_val = norm['unit'] or "dona"
                mxik = norm['mxik']

                if markup == 0 and cost_price > 0 and price > cost_price:
                    markup = ((price - cost_price) / cost_price) * Decimal('100.0')

                # Check if product exists by name or mxik
                product = None
                if mxik:
                    product = Product.objects.filter(mxik=mxik).first()
                if not product:
                    product = Product.objects.filter(name__iexact=name).first()

                is_new = False
                if product:
                    if price > 0:
                        product.price = price
                    if cost_price > 0:
                        product.cost_price = cost_price
                    if markup > 0:
                        product.markup_percentage = markup
                    if unit_val:
                        product.unit = unit_val
                    if mxik and not product.mxik:
                        product.mxik = mxik
                    if category and not product.category:
                        product.category = category
                    if department and not product.department:
                        product.department = department
                    product.save()
                    updated_count += 1
                else:
                    is_new = True
                    product = Product.objects.create(
                        name=name,
                        category=category,
                        department=department,
                        price=price,
                        cost_price=cost_price,
                        markup_percentage=markup,
                        unit=unit_val,
                        mxik=mxik,
                        is_active=True
                    )
                    created_count += 1

                imported_items.append({
                    'id': product.id,
                    'name': product.name,
                    'category': product.category.name if product.category else None,
                    'department': product.department.name if product.department else None,
                    'price': float(product.price),
                    'cost_price': float(product.cost_price),
                    'unit': product.unit,
                    'status': 'created' if is_new else 'updated'
                })

            except Exception as err:
                logger.error(f"Error importing menu row {idx}: {err}")
                errors.append(f"{idx}-qator: {str(err)}")

        total_imported = created_count + updated_count
        return Response({
            "status": "success",
            "message": f"Excel orqali {total_imported} ta taom muvaffaqiyatli yuklandi",
            "imported_rows": total_imported,
            "created_count": created_count,
            "updated_count": updated_count,
            "errors": errors,
            "products": imported_items
        }, status=status.HTTP_200_OK if total_imported > 0 else status.HTTP_400_BAD_REQUEST)
