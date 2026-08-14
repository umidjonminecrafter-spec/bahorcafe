from django.db import models
from apps.core.models import TimeStampedModel
from apps.sozlamalar.models import Branch

class Department(TimeStampedModel):
    name = models.CharField(max_length=255) # e.g. "Oshxona", "Bar", "Somsa", "Shashlik"
    ombor = models.ForeignKey('inventory.Warehouse', on_delete=models.SET_NULL, null=True, blank=True, related_name='departments')
    filial = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name='departments')
    printer = models.CharField(max_length=255, blank=True, default="")
    begunokni_chop_etish = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.filial.name if self.filial else 'Global'})"

class SemiProduct(TimeStampedModel):
    name = models.CharField(max_length=255) # e.g. "Qiyma go'sht", "Maxsus sous"
    category = models.ForeignKey('inventory.InventoryCategory', on_delete=models.SET_NULL, null=True, blank=True, related_name='semi_products')
    unit = models.CharField(max_length=50, default="kg")
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.unit})"

class SemiProductIngredient(TimeStampedModel):
    semi_product = models.ForeignKey(SemiProduct, on_delete=models.CASCADE, related_name='ingredients')
    ingredient = models.ForeignKey('inventory.InventoryProduct', on_delete=models.CASCADE, related_name='used_in_semi_products')
    brutto = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    netto = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.semi_product.name} <- {self.ingredient.name}"
