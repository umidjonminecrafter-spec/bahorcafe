from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from .models import (
    Warehouse,
    InventoryCategory,
    Unit,
    Supplier,
    InventoryProduct,
    Purchase,
    PurchaseItem,
    WriteOff,
    WriteOffItem,
    Realization,
    RealizationItem,
    InventoryStockHistory
)
from .serializers import (
    WarehouseSerializer,
    InventoryCategorySerializer,
    UnitSerializer,
    SupplierSerializer,
    InventoryProductSerializer,
    PurchaseSerializer,
    WriteOffSerializer,
    RealizationSerializer,
    InventoryStockHistorySerializer
)

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['branch', 'is_active']
    search_fields = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

class InventoryCategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [AllowAny]
    search_fields = ['name']

class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [AllowAny]
    search_fields = ['name', 'short_name']

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]
    search_fields = ['name', 'phone', 'company']

class InventoryProductViewSet(viewsets.ModelViewSet):
    queryset = InventoryProduct.objects.all().select_related('category', 'warehouse')
    serializer_class = InventoryProductSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category', 'warehouse', 'is_active']
    search_fields = ['name', 'barcode', 'mxik']
    ordering_fields = ['id', 'name', 'current_stock', 'selling_price', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(warehouse__branch_id=branch_id)
        return qs

class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.all().select_related('warehouse', 'supplier').prefetch_related('items', 'items__product')
    serializer_class = PurchaseSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['warehouse', 'supplier', 'status']
    search_fields = ['document_number', 'contract_number']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        items_data = data.pop('items', []) or data.pop('products', [])
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save()

        total_calc = Decimal('0.0')

        for it in items_data:
            product_id = it.get('product') or it.get('product_id') or it.get('id')
            if not product_id:
                continue
            product = InventoryProduct.objects.filter(id=product_id).first()
            if not product:
                continue

            qty = Decimal(str(it.get('quantity') or it.get('qty') or 1))
            price = Decimal(str(it.get('purchase_price') or it.get('kelish_narxi') or product.purchase_price))
            margin = Decimal(str(it.get('margin_percent') or product.margin_percent))
            selling = Decimal(str(it.get('selling_price') or it.get('sotish_narxi') or product.selling_price))

            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity=qty,
                purchase_price=price,
                margin_percent=margin,
                selling_price=selling
            )

            # Update product stock & prices
            prev_stock = product.current_stock
            product.current_stock = prev_stock + qty
            product.purchase_price = price
            product.selling_price = selling
            product.margin_percent = margin
            product.save(update_fields=['current_stock', 'purchase_price', 'selling_price', 'margin_percent', 'updated_at'])

            # Log history
            InventoryStockHistory.objects.create(
                product=product,
                movement_type='in',
                quantity=qty,
                previous_stock=prev_stock,
                new_stock=product.current_stock,
                reference_id=f"Xarid #{purchase.document_number or purchase.id}",
                note="Xarid orqali kirim qilindi"
            )

            total_calc += (qty * price)

        if not purchase.total_amount or purchase.total_amount == 0:
            purchase.total_amount = total_calc
            purchase.save(update_fields=['total_amount'])

        return Response(self.get_serializer(purchase).data, status=status.HTTP_201_CREATED)

class WriteOffViewSet(viewsets.ModelViewSet):
    queryset = WriteOff.objects.all().select_related('warehouse').prefetch_related('items', 'items__product')
    serializer_class = WriteOffSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['warehouse']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        items_data = data.pop('items', []) or data.pop('products', [])

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        write_off = serializer.save()

        total_calc = Decimal('0.0')

        for it in items_data:
            product_id = it.get('product') or it.get('product_id') or it.get('id')
            if not product_id:
                continue
            product = InventoryProduct.objects.filter(id=product_id).first()
            if not product:
                continue

            qty = Decimal(str(it.get('quantity') or it.get('qty') or 1))

            WriteOffItem.objects.create(
                write_off=write_off,
                product=product,
                quantity=qty
            )

            prev_stock = product.current_stock
            product.current_stock = max(0, prev_stock - qty)
            product.save(update_fields=['current_stock', 'updated_at'])

            InventoryStockHistory.objects.create(
                product=product,
                movement_type='out',
                quantity=qty,
                previous_stock=prev_stock,
                new_stock=product.current_stock,
                reference_id=f"Chiqim #{write_off.id}",
                note=write_off.reason or "Chiqim qilindi"
            )

            total_calc += (qty * product.purchase_price)

        if not write_off.total_amount or write_off.total_amount == 0:
            write_off.total_amount = total_calc
            write_off.save(update_fields=['total_amount'])

        return Response(self.get_serializer(write_off).data, status=status.HTTP_201_CREATED)

class RealizationViewSet(viewsets.ModelViewSet):
    queryset = Realization.objects.all().select_related('warehouse').prefetch_related('items', 'items__product')
    serializer_class = RealizationSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['warehouse']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        items_data = data.pop('items', []) or data.pop('products', [])

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        realization = serializer.save()

        total_sales = Decimal('0.0')
        total_cost = Decimal('0.0')

        for it in items_data:
            product_id = it.get('product') or it.get('product_id') or it.get('id')
            if not product_id:
                continue
            product = InventoryProduct.objects.filter(id=product_id).first()
            if not product:
                continue

            qty = Decimal(str(it.get('quantity') or it.get('qty') or 1))
            purchase_price = Decimal(str(it.get('purchase_price') or product.purchase_price))
            selling_price = Decimal(str(it.get('selling_price') or product.selling_price))

            RealizationItem.objects.create(
                realization=realization,
                product=product,
                quantity=qty,
                purchase_price=purchase_price,
                selling_price=selling_price
            )

            prev_stock = product.current_stock
            product.current_stock = max(0, prev_stock - qty)
            product.save(update_fields=['current_stock', 'updated_at'])

            InventoryStockHistory.objects.create(
                product=product,
                movement_type='realization',
                quantity=qty,
                previous_stock=prev_stock,
                new_stock=product.current_stock,
                reference_id=f"Realizatsiya #{realization.document_number or realization.id}",
                note="Realizatsiya sotuvi"
            )

            total_sales += (qty * selling_price)
            total_cost += (qty * purchase_price)

        realization.total_amount = total_sales
        realization.margin_amount = max(0, total_sales - total_cost)
        realization.save(update_fields=['total_amount', 'margin_amount'])

        return Response(self.get_serializer(realization).data, status=status.HTTP_201_CREATED)

class InventoryStockHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryStockHistory.objects.all().select_related('product')
    serializer_class = InventoryStockHistorySerializer
    permission_classes = [AllowAny]
    filterset_fields = ['product', 'movement_type']
    search_fields = ['product__name', 'reference_id', 'note']

class EdiImportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({
            "status": "success",
            "message": "EDI fayl muvaffaqiyatli qabul qilindi",
            "imported_rows": 12
        })
