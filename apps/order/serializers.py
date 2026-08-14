from rest_framework import serializers
from .models import Order, OrderItem
from apps.table.models import Product, Table
from apps.employee.models import Employee

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=12, decimal_places=2, read_only=True)
    department_name = serializers.CharField(source='product.department.name', read_only=True, default="")
    food_name = serializers.CharField(source='product_name_snapshot', read_only=True)
    price = serializers.DecimalField(source='unit_price', max_digits=12, decimal_places=2, required=False)
    quantity = serializers.DecimalField(source='qty', max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'order', 'product', 'product_name', 'food_name', 'product_price',
            'department_name', 'qty', 'quantity', 'unit_price', 'price',
            'cost_price', 'total_price', 'note', 'status', 'created_at', 'updated_at'
        ]

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    table_name = serializers.CharField(source='table.name', read_only=True)
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    waiter_name = serializers.CharField(source='assigned_waiter.name', read_only=True)
    assigned_waiter_name = serializers.CharField(source='assigned_waiter.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    service_fee = serializers.DecimalField(source='service_amount', max_digits=14, decimal_places=2, read_only=True)
    xizmat_haqqi = serializers.DecimalField(source='service_amount', max_digits=14, decimal_places=2, read_only=True)
    jami_summa = serializers.DecimalField(source='total_amount', max_digits=14, decimal_places=2, read_only=True)
    stol = serializers.CharField(source='table.name', read_only=True)
    ofitsiant = serializers.CharField(source='assigned_waiter.name', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'number', 'branch', 'branch_name', 'table', 'table_name', 'table_number',
            'stol', 'table_part', 'assigned_waiter', 'waiter_name', 'assigned_waiter_name',
            'ofitsiant', 'type', 'status', 'guests_count', 'base_amount', 'discount_type',
            'discount_value', 'discount_amount', 'service_percent', 'service_amount',
            'service_fee', 'xizmat_haqqi', 'total_amount', 'jami_summa', 'payment_type',
            'cash_amount', 'card_amount', 'note', 'opened_at', 'paid_at', 'closed_at',
            'items', 'created_at', 'updated_at'
        ]
