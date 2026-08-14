from django.db import models
from apps.core.models import TimeStampedModel
from apps.sozlamalar.models import Branch

class Table(TimeStampedModel):
    STATUS_CHOICES = (
        ('free', 'Bo\'sh'),
        ('busy', 'Band'),
        ('payment', 'To\'lov'),
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='tables', null=True, blank=True)
    name = models.CharField(max_length=100) # e.g. "1-stol", "Stol 1", "VIP 1"
    table_number = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='free')
    is_busy = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def number(self):
        return self.table_number or self.id

class TablePart(TimeStampedModel):
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='parts')
    name = models.CharField(max_length=100) # e.g. "Guruh 1"
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.table.name} - {self.name}"

class TableLayout(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='table_layouts', null=True, blank=True)
    layout_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Layout ({self.branch.name if self.branch else 'Global'})"

class ProductCategory(TimeStampedModel):
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=100, blank=True, default="")
    image = models.ImageField(upload_to='categories/', null=True, blank=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name_plural = "Product Categories"

    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    department = models.ForeignKey('kitchen.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # selling price
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # tannarx
    markup_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0.0) # ustama %
    unit = models.CharField(max_length=50, default="dona")
    mxik = models.CharField(max_length=100, blank=True, default="")
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    is_weight_recipe = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} - {self.price} UZS"

    @property
    def selling_price(self):
        return self.price

class ProductIngredient(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ingredients')
    maxsulot = models.ForeignKey('inventory.InventoryProduct', on_delete=models.CASCADE, related_name='used_in_recipes', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=3, default=0.0) # e.g. 0.250 kg
    unit = models.CharField(max_length=50, default="kg")

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} <- {self.maxsulot.name if self.maxsulot else 'N/A'} ({self.amount} {self.unit})"
