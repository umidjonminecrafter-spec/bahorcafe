from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Table, TablePart, TableLayout, ProductCategory, Product, ProductIngredient
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
