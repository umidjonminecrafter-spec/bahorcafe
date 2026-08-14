from rest_framework import serializers
from .models import Table, TablePart, TableLayout, ProductCategory, Product, ProductIngredient
from apps.inventory.models import InventoryProduct

class TablePartSerializer(serializers.ModelSerializer):
    class Meta:
        model = TablePart
        fields = '__all__'

class TableSerializer(serializers.ModelSerializer):
    parts = TablePartSerializer(many=True, read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    table_number = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Table
        fields = ['id', 'branch', 'branch_name', 'name', 'table_number', 'status', 'is_busy', 'is_active', 'parts', 'created_at', 'updated_at']

    def create(self, validated_data):
        if not validated_data.get('table_number'):
            last = Table.objects.order_by('-id').first()
            validated_data['table_number'] = (last.id + 1) if last else 1
        return super().create(validated_data)

class TableLayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableLayout
        fields = '__all__'

class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'

class ProductIngredientSerializer(serializers.ModelSerializer):
    maxsulot_name = serializers.CharField(source='maxsulot.name', read_only=True)
    maxsulot_unit = serializers.CharField(source='maxsulot.unit', read_only=True)
    maxsulot_cost = serializers.DecimalField(source='maxsulot.purchase_price', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ProductIngredient
        fields = ['id', 'product', 'maxsulot', 'maxsulot_name', 'maxsulot_unit', 'maxsulot_cost', 'amount', 'unit', 'created_at', 'updated_at']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    ingredients = ProductIngredientSerializer(many=True, read_only=True)
    selling_price = serializers.DecimalField(source='price', max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_name', 'department', 'department_name',
            'name', 'price', 'selling_price', 'cost_price', 'markup_percentage',
            'unit', 'mxik', 'image', 'is_weight_recipe', 'is_active', 'ingredients',
            'created_at', 'updated_at'
        ]
