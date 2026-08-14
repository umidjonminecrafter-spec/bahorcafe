from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from apps.core.models import TimeStampedModel
from apps.sozlamalar.models import Branch

class Role(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    salary_type = models.CharField(max_length=50, default="fixed")
    salary_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name

class RoleModulePermission(TimeStampedModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='module_permissions')
    module = models.CharField(max_length=100) # e.g. 'dashboard', 'menu', 'kassa', 'ombor', etc.
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'module')
        ordering = ['module']

    def __str__(self):
        return f"{self.role.name} - {self.module}"

class Employee(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile', null=True, blank=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, unique=True, db_index=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    role_name = models.CharField(max_length=100, blank=True, default="") # fallback string representation
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    quick_pin = models.CharField(max_length=128, blank=True, default="") # hashed 4-digit PIN
    pin_is_set = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def set_pin(self, raw_pin):
        self.quick_pin = make_password(str(raw_pin).strip())
        self.pin_is_set = True
        self.save(update_fields=['quick_pin', 'pin_is_set', 'updated_at'])

    def check_pin(self, raw_pin):
        if not self.quick_pin:
            return False
        # Allow checking hashed PIN or raw (for backward compatibility if any)
        if self.quick_pin == str(raw_pin).strip():
            return True
        return check_password(str(raw_pin).strip(), self.quick_pin)

class EmployeePermission(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='permissions_list')
    module = models.CharField(max_length=100)
    action = models.CharField(max_length=50, default='view') # 'view', 'create', 'edit', 'delete'
    value = models.BooleanField(default=True)
    can_payment = models.BooleanField(default=False)
    can_discount = models.BooleanField(default=False)
    can_cancel_order = models.BooleanField(default=False)
    can_income = models.BooleanField(default=False)

    class Meta:
        ordering = ['module', 'action']

    def __str__(self):
        return f"{self.employee.name} - {self.module}_{self.action}"

class SalaryScheme(TimeStampedModel):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name='salary_scheme')
    salary_type = models.CharField(max_length=50, default='fiksa') # 'fiksa', 'foizli', 'soatlik', 'fiksa_foiz', 'smena', 'ball'
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.employee.name} - {self.salary_type}"

class SalaryRecord(TimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salary_records')
    month = models.CharField(max_length=50, blank=True, default="")
    salary_type = models.CharField(max_length=50, default='fiksa')
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    calculated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    bonus = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    penalty = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    status = models.CharField(max_length=50, default='paid') # 'paid', 'pending'
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee.name} - {self.paid_amount} ({self.created_at})"
