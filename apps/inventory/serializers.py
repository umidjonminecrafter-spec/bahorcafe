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
    nomi = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)
    qty = serializers.DecimalField(source='quantity', max_digits=10, decimal_places=3, read_only=True)
    cost_price = serializers.DecimalField(source='purchase_price', max_digits=12, decimal_places=2, read_only=True)
    sale_price = serializers.DecimalField(source='selling_price', max_digits=12, decimal_places=2, read_only=True)
    margin = serializers.DecimalField(source='margin_percent', max_digits=6, decimal_places=2, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseItem
        fields = [
            'id', 'purchase', 'product', 'product_name', 'nomi', 'product_unit', 'unit',
            'quantity', 'qty', 'purchase_price', 'cost_price', 'margin_percent', 'margin',
            'selling_price', 'sale_price', 'total_price'
        ]

    def get_total_price(self, obj):
        return float(obj.quantity * obj.purchase_price)

class PurchaseSerializer(serializers.ModelSerializer):
    items = PurchaseItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    ombor = serializers.CharField(source='warehouse.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    tamiNotchi = serializers.CharField(source='supplier.name', read_only=True)
    sana = serializers.DateField(source='date', read_only=True)
    hujjat_raqami = serializers.CharField(source='document_number', read_only=True)
    doc_no = serializers.CharField(source='document_number', read_only=True)
    tushum_summasi = serializers.DecimalField(source='total_amount', max_digits=14, decimal_places=2, read_only=True)
    total = serializers.DecimalField(source='total_amount', max_digits=14, decimal_places=2, read_only=True)
    summa = serializers.DecimalField(source='total_amount', max_digits=14, decimal_places=2, read_only=True)
    items_count = serializers.SerializerMethodField()
    mahsulotlar_soni = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = [
            'id', 'warehouse', 'warehouse_name', 'ombor', 'supplier', 'supplier_name', 'tamiNotchi',
            'document_number', 'hujjat_raqami', 'doc_no', 'contract_number', 'date', 'sana',
            'total_amount', 'total', 'summa', 'tushum_summasi', 'status', 'notes',
            'items_count', 'mahsulotlar_soni', 'items', 'created_at', 'updated_at'
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_mahsulotlar_soni(self, obj):
        return obj.items.count()

class WriteOffItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    nomi = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)
    qty = serializers.DecimalField(source='quantity', max_digits=10, decimal_places=3, read_only=True)

    class Meta:
        model = WriteOffItem
        fields = ['id', 'write_off', 'product', 'product_name', 'nomi', 'product_unit', 'unit', 'quantity', 'qty']

class WriteOffSerializer(serializers.ModelSerializer):
    items = WriteOffItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    ombor = serializers.CharField(source='warehouse.name', read_only=True)
    sana = serializers.DateField(source='date', read_only=True)
    sabab = serializers.CharField(source='reason', read_only=True)
    summa = serializers.DecimalField(source='total_amount', max_digits=14, decimal_places=2, read_only=True)
    items_count = serializers.SerializerMethodField()
    mahsulotlar_soni = serializers.SerializerMethodField()

    class Meta:
        model = WriteOff
        fields = [
            'id', 'warehouse', 'warehouse_name', 'ombor', 'reason', 'sabab', 'note',
            'date', 'sana', 'total_amount', 'summa', 'items_count', 'mahsulotlar_soni',
            'items', 'created_at', 'updated_at'
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_mahsulotlar_soni(self, obj):
        return obj.items.count()

class RealizationItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    nomi = serializers.CharField(source='product.name', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)
    qty = serializers.DecimalField(source='quantity', max_digits=10, decimal_places=3, read_only=True)
    cost_price = serializers.DecimalField(source='purchase_price', max_digits=12, decimal_places=2, read_only=True)
    sale_price = serializers.DecimalField(source='selling_price', max_digits=12, decimal_places=2, read_only=True)
    total_price = serializers.SerializerMethodField()
    margin_amount = serializers.SerializerMethodField()

    class Meta:
        model = RealizationItem
        fields = [
            'id', 'realization', 'product', 'product_name', 'nomi', 'product_unit', 'unit',
            'quantity', 'qty', 'purchase_price', 'cost_price', 'selling_price', 'sale_price',
            'total_price', 'margin_amount'
        ]

    def get_total_price(self, obj):
        return float(obj.quantity * obj.selling_price)

    def get_margin_amount(self, obj):
        return float(obj.quantity * (obj.selling_price - obj.purchase_price))

class RealizationSerializer(serializers.ModelSerializer):
    items = RealizationItemSerializer(many=True, read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    ombor = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_id = serializers.IntegerField(source='warehouse.id', read_only=True)
    ombor_id = serializers.IntegerField(source='warehouse.id', read_only=True)
    hujjat_raqami = serializers.CharField(source='document_number', read_only=True)
    doc_no = serializers.CharField(source='document_number', read_only=True)
    kontragent = serializers.CharField(source='agent', read_only=True)
    contragent = serializers.CharField(source='agent', read_only=True)
    sana = serializers.DateField(source='date', read_only=True)
    umumiy_summa = serializers.DecimalField(source='total_amount', max_digits=14, decimal_places=2, read_only=True)
    summa = serializers.DecimalField(source='total_amount', max_digits=14, decimal_places=2, read_only=True)
    total = serializers.DecimalField(source='total_amount', max_digits=14, decimal_places=2, read_only=True)
    ustama = serializers.DecimalField(source='margin_amount', max_digits=14, decimal_places=2, read_only=True)
    tovar_soni = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    cost_total = serializers.SerializerMethodField()
    tannarx = serializers.SerializerMethodField()

    class Meta:
        model = Realization
        fields = [
            'id', 'warehouse', 'warehouse_id', 'warehouse_name', 'ombor', 'ombor_id',
            'agent', 'kontragent', 'contragent', 'document_number', 'hujjat_raqami', 'doc_no',
            'date', 'sana', 'total_amount', 'total', 'summa', 'umumiy_summa',
            'margin_amount', 'ustama', 'cost_total', 'tannarx', 'notes',
            'tovar_soni', 'items_count', 'items', 'created_at', 'updated_at'
        ]

    def get_tovar_soni(self, obj):
        return obj.items.count()

    def get_items_count(self, obj):
        return obj.items.count()

    def get_cost_total(self, obj):
        total_cost = sum([it.quantity * it.purchase_price for it in obj.items.all()], 0)
        return float(total_cost)

    def get_tannarx(self, obj):
        return self.get_cost_total(obj)

class InventoryStockHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    unit = serializers.CharField(source='product.unit', read_only=True)

    class Meta:
        model = InventoryStockHistory
        fields = ['id', 'product', 'product_name', 'unit', 'movement_type', 'quantity', 'previous_stock', 'new_stock', 'reference_id', 'note', 'created_at']

