from django.db import models
from django.utils import timezone
from apps.core.models import TimeStampedModel
from apps.sozlamalar.models import Branch
from apps.employee.models import Employee
from apps.order.models import Order

class FinanceAccount(TimeStampedModel):
    ACCOUNT_TYPE_CHOICES = (
        ('CASH', 'Naqd pul (Kassa)'),
        ('NON_CASH', 'Plastik karta (Terminal)'),
        ('BANK', 'Hisob raqam (Bank)'),
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='finance_accounts', null=True, blank=True)
    name = models.CharField(max_length=255) # e.g. "Asosiy naqd kassa", "Humo/Uzcard terminal"
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='CASH')
    balance = models.DecimalField(max_digits=16, decimal_places=2, default=0.0)
    currency = models.CharField(max_length=10, default='UZS')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.balance} {self.currency})"

class FinanceCategory(TimeStampedModel):
    CATEGORY_TYPE_CHOICES = (
        ('INCOME', 'Daromad'),
        ('EXPENSE', 'Xarajat'),
    )
    name = models.CharField(max_length=255) # e.g. "Sotuv tushumi", "Mahsulot xaridi", "Xodimlar oyligi", "Ijara", "Kommunal"
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES, default='EXPENSE')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']
        verbose_name_plural = "Finance Categories"

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"

class FinanceTransaction(TimeStampedModel):
    TRANSACTION_TYPE_CHOICES = (
        ('INCOME', 'Kirim / Daromad'),
        ('EXPENSE', 'Chiqim / Xarajat'),
    )
    SOURCE_CHOICES = (
        ('kassa', 'Kassa sotuv tushumi'),
        ('order', 'Buyurtma to\'lovi'),
        ('salary', 'Maosh to\'lovi'),
        ('purchase', 'Ombor xaridi'),
        ('manual', 'Qo\'lda kiritilgan'),
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='finance_transactions', null=True, blank=True)
    account = models.ForeignKey(FinanceAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    category = models.ForeignKey(FinanceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default='INCOME')
    payment_type = models.CharField(max_length=50, default='cash') # 'cash', 'card', 'bank'
    amount = models.DecimalField(max_digits=16, decimal_places=2, default=0.0)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='manual')
    
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_transactions')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_transactions')
    description = models.TextField(blank=True, default="")
    date = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"[{self.transaction_type}] {self.amount} UZS - {self.description or self.source}"
