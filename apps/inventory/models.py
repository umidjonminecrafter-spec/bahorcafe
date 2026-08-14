from django.db import models
from apps.core.models import TimeStampedModel
from apps.sozlamalar.models import Branch

class Warehouse(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='warehouses', null=True, blank=True)
    name = models.CharField(max_length=255) # e.g. "Asosiy ombor", "Oshxona ombori"
    address = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.branch.name if self.branch else 'Global'})"

class InventoryCategory(TimeStampedModel):
    name = models.CharField(max_length=255) # e.g. "Go'sht mahsulotlari", "Sabzavotlar", "Ichimliklar"
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']
        verbose_name_plural = "Inventory Categories"

    def __str__(self):
        return self.name

class Unit(TimeStampedModel):
    name = models.CharField(max_length=50) # "kilogramm", "dona", "litr", "gramm"
    short_name = models.CharField(max_length=20) # "kg", "dona", "l", "g"

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.short_name or self.name

class Supplier(TimeStampedModel):
    name = models.CharField(max_length=255) # e.g. "Akrom Aka", "Agro Meat MCHJ"
    phone = models.CharField(max_length=50, blank=True, default="")
    company = models.CharField(max_length=255, blank=True, default="")
    address = models.CharField(max_length=500, blank=True, default="")
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

class InventoryProduct(TimeStampedModel):
    category = models.ForeignKey(InventoryCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=255) # e.g. "Mol go'shti (lahm)", "Piyoz", "Coca-Cola 1.5L"
    barcode = models.CharField(max_length=100, blank=True, default="")
    mxik = models.CharField(max_length=100, blank=True, default="")
    unit = models.CharField(max_length=50, default="kg")
    
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # kelish narxi
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # sotish narxi
    wholesale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) # ulgurji narx
    margin_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.0) # ustama %
    qqs_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0) # QQS %
    
    min_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    max_stock = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    current_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0.0) # joriy qoldiq
    
    image = models.ImageField(upload_to='inventory/', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.current_stock} {self.unit})"

class Purchase(TimeStampedModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    document_number = models.CharField(max_length=100, blank=True, default="")
    contract_number = models.CharField(max_length=100, blank=True, default="")
    date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    status = models.CharField(max_length=50, default="completed")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Purchase #{self.document_number or self.id} - {self.total_amount} UZS"

class PurchaseItem(TimeStampedModel):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(InventoryProduct, on_delete=models.CASCADE, related_name='purchase_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    margin_percent = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class WriteOff(TimeStampedModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='write_offs')
    reason = models.CharField(max_length=255, default="Buzuqlik / Zararlanish")
    note = models.TextField(blank=True, default="")
    date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"WriteOff #{self.id} - {self.total_amount} UZS"

class WriteOffItem(TimeStampedModel):
    write_off = models.ForeignKey(WriteOff, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(InventoryProduct, on_delete=models.CASCADE, related_name='write_off_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class Realization(TimeStampedModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='realizations')
    agent = models.CharField(max_length=255, blank=True, default="")
    document_number = models.CharField(max_length=100, blank=True, default="")
    date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    margin_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"Realization #{self.document_number or self.id} - {self.total_amount} UZS"

class RealizationItem(TimeStampedModel):
    realization = models.ForeignKey(Realization, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(InventoryProduct, on_delete=models.CASCADE, related_name='realization_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class InventoryStockHistory(TimeStampedModel):
    MOVEMENT_CHOICES = (
        ('in', 'Kirim (Xarid)'),
        ('out', 'Chiqim (Buzuqlik/Harakat)'),
        ('realization', 'Realizatsiya (Sotuv)'),
        ('auto_deduct', 'POS Avto Chiqim'),
        ('audit', 'Inventarizatsiya'),
    )
    product = models.ForeignKey(InventoryProduct, on_delete=models.CASCADE, related_name='stock_history')
    movement_type = models.CharField(max_length=50, choices=MOVEMENT_CHOICES, default='in')
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0.0)
    previous_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0.0)
    new_stock = models.DecimalField(max_digits=12, decimal_places=3, default=0.0)
    reference_id = models.CharField(max_length=100, blank=True, default="")
    note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name}: {self.movement_type} ({self.quantity}) -> {self.new_stock}"
