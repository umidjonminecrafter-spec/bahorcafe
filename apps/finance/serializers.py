from rest_framework import serializers
from .models import FinanceAccount, FinanceCategory, FinanceTransaction

class FinanceAccountSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = FinanceAccount
        fields = '__all__'

class FinanceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceCategory
        fields = '__all__'

class FinanceTransactionSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    employee_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model = FinanceTransaction
        fields = [
            'id', 'branch', 'branch_name', 'account', 'account_name',
            'category', 'category_name', 'transaction_type', 'payment_type',
            'amount', 'source', 'order', 'employee', 'employee_name',
            'description', 'date', 'created_at', 'updated_at'
        ]
