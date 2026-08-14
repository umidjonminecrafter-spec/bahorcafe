from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.sozlamalar.models import Branch
from apps.employee.models import Employee
from apps.table.models import Table, TablePart, Product

class Order(TimeStampedModel):
    ORDER_TYPE_CHOICES = (
        ('dine_in', 'Zalda (Dine-in)'),
        ('takeaway', 'Olib ketish (Takeaway)'),
        ('delivery', 'Yetkazib berish (Delivery)'),
    )
    STATUS_CHOICES = (
        ('open', 'Ochiq'),
        ('sent_to_kitchen', 'Oshxonaga yuborilgan'),
        ('ready', 'Tayyor'),
        ('paid', 'To\'langan'),
        ('closed', 'Yopilgan'),
        ('cancelled', 'Bekor qilingan'),
    )
    PAYMENT_CHOICES = (
        ('cash', 'Naqd'),
        ('card', 'Plastik karta'),
        ('mixed', 'Aralash'),
        ('click', 'Click'),
        ('payme', 'Payme'),
    )

    number = models.IntegerField(db_index=True, null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    table_part = models.ForeignKey(TablePart, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    assigned_waiter = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_orders')
    
    type = models.CharField(max_length=50, choices=ORDER_TYPE_CHOICES, default='dine_in')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='open')
    guests_count = models.IntegerField(default=1)
    
    base_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    discount_type = models.CharField(max_length=20, default='percent') # 'percent' or 'fixed'
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    service_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    service_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    
    payment_type = models.CharField(max_length=50, choices=PAYMENT_CHOICES, null=True, blank=True)
    cash_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    card_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    
    note = models.TextField(blank=True, default="")
    opened_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']

    def save(self, *args, **kwargs):
        if not self.number:
            from django.db.models import Max
            max_num = Order.objects.aggregate(m=Max('number'))['m']
            self.number = (max_num + 1) if max_num else 1001
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.number or self.id} ({self.get_status_display()}) - {self.total_amount} UZS"

    def recalculate_totals(self):
        items = self.items.all()
        subtotal = sum((item.qty * item.unit_price for item in items), 0)
        self.base_amount = subtotal
        
        # Calculate discount
        if self.discount_type == 'percent':
            self.discount_amount = (subtotal * self.discount_value / 100) if self.discount_value > 0 else 0
        else:
            self.discount_amount = self.discount_value or 0
        
        after_discount = max(0, subtotal - self.discount_amount)
        self.service_amount = (after_discount * self.service_percent / 100) if self.service_percent > 0 else 0
        self.total_amount = after_discount + self.service_amount
        self.save(update_fields=['base_amount', 'discount_amount', 'service_amount', 'total_amount', 'updated_at'])

class OrderItem(TimeStampedModel):
    ITEM_STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('cooking', 'Tayyorlanmoqda'),
        ('ready', 'Tayyor'),
        ('served', 'Yetkazildi'),
        ('cancelled', 'Bekor qilindi'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    qty = models.DecimalField(max_digits=10, decimal_places=2, default=1.0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    total_price = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    
    note = models.CharField(max_length=255, blank=True, default="") # e.g. "saboy", "kam yog'li"
    status = models.CharField(max_length=50, choices=ITEM_STATUS_CHOICES, default='pending')
    
    product_name_snapshot = models.CharField(max_length=255, blank=True, default="")
    kitchen_name_snapshot = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ['id']

    def save(self, *args, **kwargs):
        if not self.unit_price and self.product:
            self.unit_price = self.product.price
        if not self.cost_price and self.product:
            self.cost_price = self.product.cost_price
        if not self.product_name_snapshot and self.product:
            self.product_name_snapshot = self.product.name
        if not self.kitchen_name_snapshot and self.product and self.product.department:
            self.kitchen_name_snapshot = self.product.department.name
        self.total_price = (self.qty or 0) * (self.unit_price or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_name_snapshot or self.product.name} x {self.qty}"
