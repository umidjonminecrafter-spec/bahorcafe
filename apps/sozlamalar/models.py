from django.db import models
from apps.core.models import TimeStampedModel

class Branch(TimeStampedModel):
    name = models.CharField(max_length=255, default="Bahor Cafe")
    city = models.CharField(max_length=255, default="Farg'ona", blank=True)
    address = models.CharField(max_length=500, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        ordering = ['id']

    def __str__(self):
        return self.name

class RestaurantSettings(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='restaurant_settings', null=True, blank=True)
    name = models.CharField(max_length=255, default="Bahor Cafe")
    address = models.CharField(max_length=500, default="Toshkent sh., Mustaqillik ko'chasi")
    phone = models.CharField(max_length=50, default="+998 90 123 45 67")
    description = models.TextField(blank=True, default="")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Restaurant Settings"
        verbose_name_plural = "Restaurant Settings"

    def __str__(self):
        return f"{self.name} ({self.branch.name if self.branch else 'All'})"

class TaxSettings(TimeStampedModel):
    CALC_CHOICES = (
        ('auto', 'Avtomatik'),
        ('manual', 'Qo\'lda'),
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='tax_settings', null=True, blank=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    service_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    calculation_type = models.CharField(max_length=20, choices=CALC_CHOICES, default='auto')

    class Meta:
        verbose_name = "Tax & Service Settings"

    def __str__(self):
        return f"Tax: {self.tax_percent}%, Service: {self.service_percent}%"

class ReceiptSettings(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='receipt_settings', null=True, blank=True)
    cafe_name = models.CharField(max_length=255, default="Bahor Cafe")
    address = models.CharField(max_length=500, default="Toshkent sh., Mustaqillik ko'chasi")
    phone = models.CharField(max_length=50, default="+998901234567")
    footer_text = models.CharField(max_length=500, default="Telegram kanalimizga obuna bo'ling!")
    
    show_cafe_name = models.BooleanField(default=True)
    show_sana = models.BooleanField(default=True)
    show_ish_vaqti = models.BooleanField(default=True)
    show_sotuvchi = models.BooleanField(default=True)
    show_kassir = models.BooleanField(default=True)
    show_mijoz = models.BooleanField(default=True)
    show_kontaktlar = models.BooleanField(default=True)
    show_inn = models.BooleanField(default=True)
    show_yuridik_shaxs = models.BooleanField(default=True)
    show_manzil = models.BooleanField(default=False)
    show_mijoz_raqami = models.BooleanField(default=True)
    show_eslatma = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Receipt Settings"

    def __str__(self):
        return f"Receipt ({self.cafe_name})"

class OrderFlowSettings(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='order_flow_settings', null=True, blank=True)
    auto_kitchen = models.BooleanField(default=True)
    signal = models.BooleanField(default=True)
    bill_btn = models.BooleanField(default=True)
    served = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Order Flow Settings"

    def __str__(self):
        return f"Order Flow ({self.branch.name if self.branch else 'Global'})"

class TelegramBotSettings(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='telegram_settings', null=True, blank=True)
    bot_token = models.CharField(max_length=255, blank=True, default="")
    chat_id = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    notify_order_paid = models.BooleanField(default=True, verbose_name="To'lov bo'lganda chek yuborish")
    notify_order_cancelled = models.BooleanField(default=True, verbose_name="Bekor qilingan buyurtma xabari")
    notify_daily_report = models.BooleanField(default=True, verbose_name="Kunlik hisobot yuborish")
    daily_report_time = models.CharField(max_length=10, default="20:00")

    class Meta:
        verbose_name = "Telegram Bot Settings"
        verbose_name_plural = "Telegram Bot Settings"

    def __str__(self):
        return f"Telegram Bot ({self.chat_id or 'No Chat ID'})"

