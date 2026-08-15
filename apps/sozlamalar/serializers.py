from rest_framework import serializers
from .models import Branch, RestaurantSettings, TaxSettings, ReceiptSettings, OrderFlowSettings, TelegramBotSettings

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'

class RestaurantSettingsSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = RestaurantSettings
        fields = '__all__'

class TaxSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxSettings
        fields = '__all__'

class ReceiptSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptSettings
        fields = '__all__'

class OrderFlowSettingsSerializer(serializers.ModelSerializer):
    # Frontend keys mapping: autoKitchen, signal, billBtn, served
    autoKitchen = serializers.BooleanField(source='auto_kitchen', required=False)
    billBtn = serializers.BooleanField(source='bill_btn', required=False)

    class Meta:
        model = OrderFlowSettings
        fields = ['id', 'branch', 'auto_kitchen', 'autoKitchen', 'signal', 'bill_btn', 'billBtn', 'served', 'created_at', 'updated_at']

class TelegramBotSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramBotSettings
        fields = '__all__'

