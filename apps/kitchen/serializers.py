from rest_framework import serializers
from .models import Department, SemiProduct, SemiProductIngredient
from apps.table.models import Product, ProductCategory, ProductIngredient
from apps.table.serializers import ProductSerializer, ProductCategorySerializer, ProductIngredientSerializer

class DepartmentSerializer(serializers.ModelSerializer):
    ombor_nomi = serializers.CharField(source='ombor.name', read_only=True)
    filial_nomi = serializers.CharField(source='filial.name', read_only=True)
    nomi = serializers.CharField(source='name', required=False)

    class Meta:
        model = Department
        fields = ['id', 'name', 'nomi', 'ombor', 'ombor_nomi', 'filial', 'filial_nomi', 'printer', 'begunokni_chop_etish', 'is_active', 'created_at', 'updated_at']

class SemiProductIngredientSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)

    class Meta:
        model = SemiProductIngredient
        fields = ['id', 'semi_product', 'ingredient', 'ingredient_name', 'ingredient_unit', 'brutto', 'netto', 'cost_price']

class SemiProductSerializer(serializers.ModelSerializer):
    ingredients = SemiProductIngredientSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    nomi = serializers.CharField(source='name', required=False)
    olchov = serializers.CharField(source='unit', required=False)

    class Meta:
        model = SemiProduct
        fields = ['id', 'name', 'nomi', 'category', 'category_name', 'unit', 'olchov', 'cost_price', 'is_active', 'ingredients', 'created_at', 'updated_at']
