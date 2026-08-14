from rest_framework import serializers
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

class WarehouseSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Warehouse
        fields = '__all__'

class InventoryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCategory
        fields = '__all__'

class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class InventoryProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    nomi = serializers.CharField(source='name', required=False)
    shtrix_kod = serializers.CharField(source='barcode', required=False, allow_blank=True)
    kelish_narxi = serializers.DecimalField(source='purchase_price', max_digits=12, decimal_places=2, required=False)
    sotish_narxi = serializers.DecimalField(source='selling_price', max_digits=12, decimal_places=2, required=False)
    qoldiq = serializers.DecimalField(source='current_stock', max_digits=12, decimal_places=3, required=False)

    class Meta:
        model = InventoryProduct
        fields = [
            'id', 'category', 'category_name', 'warehouse', 'warehouse_name',
            'name', 'nomi', 'barcode', 'shtrix_kod', 'mxik', 'unit',
            'purchase_price', 'kelish_narxi', 'selling_price', 'sotish_narxi',
            'wholesale_price', 'margin_percent', 'qqs_rate', 'min_stock', 'max_stock',
            'current_stock', 'qoldiq', 'image', 'is_active', 'created_at', 'updated_at'
        ]

class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)

    class Meta:
        model = PurchaseItem
        fields = ['id', 'purchase', 'product', 'product_name', 'product_unit', 'quantity', 'purchase_price', 'margin_percent', 'selling_price']

class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = Purchase
        fields = ['id', 'warehouse', 'warehouse_name', 'supplier', 'supplier_name', 'document_number', 'contract_number', 'date', 'total_amount', 'status', 'notes', 'items', 'created_at', 'updated_at']

class WriteOffItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)

    class Meta:
        model = WriteOffItem
        fields = ['id', 'write_off', 'product', 'product_name', 'product_unit', 'quantity']

class WriteOffSerializer(serializers.ModelSerializer):
    items = WriteOffItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = WriteOff
        fields = ['id', 'warehouse', 'warehouse_name', 'reason', 'note', 'date', 'total_amount', 'items', 'created_at', 'updated_at']

class RealizationItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)

    class Meta:
        model = RealizationItem
        fields = ['id', 'realization', 'product', 'product_name', 'product_unit', 'quantity', 'purchase_price', 'selling_price']

class RealizationSerializer(serializers.ModelSerializer):
    items = RealizationItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)

    class Meta:
        model = Realization
        fields = ['id', 'warehouse', 'warehouse_name', 'agent', 'document_number', 'date', 'total_amount', 'margin_amount', 'notes', 'items', 'created_at', 'updated_at']

class InventoryStockHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)

    class Meta:
        model = InventoryStockHistory
        fields = ['id', 'product', 'product_name', 'unit', 'movement_type', 'quantity', 'previous_stock', 'new_stock', 'reference_id', 'note', 'created_at']
