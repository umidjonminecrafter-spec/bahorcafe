from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Role, RoleModulePermission, Employee, EmployeePermission, SalaryScheme, SalaryRecord

class RoleModulePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleModulePermission
        fields = ['id', 'role', 'module', 'can_view', 'can_create', 'can_edit', 'can_delete']

class RoleSerializer(serializers.ModelSerializer):
    module_permissions = RoleModulePermissionSerializer(many=True, read_only=True)
    role_name = serializers.CharField(source='name', required=False)
    salaryType = serializers.CharField(source='salary_type', required=False)
    salaryAmount = serializers.DecimalField(source='salary_amount', max_digits=12, decimal_places=2, required=False)

    class Meta:
        model = Role
        fields = ['id', 'name', 'role_name', 'salary_type', 'salaryType', 'salary_amount', 'salaryAmount', 'module_permissions', 'created_at', 'updated_at']

class EmployeePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeePermission
        fields = ['id', 'employee', 'module', 'action', 'value', 'can_payment', 'can_discount', 'can_cancel_order', 'can_income']

class SalarySchemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryScheme
        fields = ['id', 'employee', 'salary_type', 'params', 'created_at', 'updated_at']

class SalaryRecordSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)

    class Meta:
        model = SalaryRecord
        fields = ['id', 'employee', 'employee_name', 'month', 'salary_type', 'amount', 'calculated_amount', 'paid_amount', 'bonus', 'penalty', 'status', 'notes', 'created_at', 'updated_at']

class EmployeeSerializer(serializers.ModelSerializer):
    role_name = serializers.SerializerMethodField()
    role_details = RoleSerializer(source='role', read_only=True)
    permissions = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    pin = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'name', 'phone', 'role', 'role_name', 'role_details',
            'branch', 'pin_is_set', 'is_active', 'last_login', 'permissions',
            'password', 'pin', 'created_at', 'updated_at'
        ]

    def get_role_name(self, obj):
        if obj.role:
            return obj.role.name
        return obj.role_name or "Xodim"

    def get_permissions(self, obj):
        perms = {}
        # 1. Add role permissions
        if obj.role:
            for p in obj.role.module_permissions.all():
                perms[f"{p.module}_view"] = p.can_view
                perms[f"{p.module}_create"] = p.can_create
                perms[f"{p.module}_edit"] = p.can_edit
                perms[f"{p.module}_delete"] = p.can_delete

        # 2. Add individual employee permissions
        for ep in obj.permissions_list.all():
            perms[f"{ep.module}_{ep.action}"] = ep.value
            if ep.can_payment: perms['can_payment'] = True
            if ep.can_discount: perms['can_discount'] = True
            if ep.can_cancel_order: perms['can_cancel_order'] = True
            if ep.can_income: perms['can_income'] = True

        return perms

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        pin = validated_data.pop('pin', None)
        phone = validated_data.get('phone', '')

        # Create or link user
        username = phone.replace('+', '').strip() or validated_data.get('name', 'emp').lower()
        user, created = User.objects.get_or_create(username=username)
        if password:
            user.set_password(password)
            user.save()

        validated_data['user'] = user
        employee = super().create(validated_data)

        if pin:
            employee.set_pin(pin)

        return employee

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        pin = validated_data.pop('pin', None)

        if password and instance.user:
            instance.user.set_password(password)
            instance.user.save()

        if pin:
            instance.set_pin(pin)

        return super().update(instance, validated_data)
