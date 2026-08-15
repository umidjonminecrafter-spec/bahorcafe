from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils import timezone
from decimal import Decimal
import math
import logging

logger = logging.getLogger('bahor_app')

from .models import Role, RoleModulePermission, Employee, EmployeePermission, SalaryScheme, SalaryRecord
from .serializers import (
    RoleSerializer,
    RoleModulePermissionSerializer,
    EmployeeSerializer,
    EmployeePermissionSerializer,
    SalarySchemeSerializer,
    SalaryRecordSerializer
)

def normalize_phone(phone):
    if not phone:
        return ""
    p = str(phone).strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if p.startswith("+"):
        p = p[1:]
    return p

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone') or request.data.get('username')
        password = request.data.get('password')

        if not phone or not password:
            return Response(
                {"error": "Telefon raqami va parol kiritilishi shart"},
                status=status.HTTP_400_BAD_REQUEST
            )

        norm_phone = normalize_phone(phone)
        employee = Employee.objects.filter(phone__icontains=norm_phone).first()

        if not employee:
            # Fallback to direct username
            user = User.objects.filter(username=norm_phone).first()
            if user and hasattr(user, 'employee_profile'):
                employee = user.employee_profile

        if not employee or not employee.user:
            return Response(
                {"error": "Foydalanuvchi topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        user = authenticate(username=employee.user.username, password=password)
        if not user:
            # Direct check if user.check_password succeeds
            if employee.user.check_password(password):
                user = employee.user
            else:
                return Response(
                    {"error": "Telefon raqami yoki parol noto'g'ri"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        token, _ = Token.objects.get_or_create(user=user)
        employee.last_login = timezone.now()
        employee.save(update_fields=['last_login', 'updated_at'])

        serializer = EmployeeSerializer(employee)
        data = serializer.data
        logger.info(f"Foydalanuvchi tizimga kirdi (Password): {employee.name} ({employee.phone})")
        return Response({
            "token": token.key,
            "user": data,
            "employee": data,
        })

class PinLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone')
        pin = request.data.get('quick_pin') or request.data.get('pin')

        if not phone or not pin:
            return Response(
                {"error": "Telefon raqami va PIN kod kiritilishi shart"},
                status=status.HTTP_400_BAD_REQUEST
            )

        norm_phone = normalize_phone(phone)
        employee = Employee.objects.filter(phone__icontains=norm_phone).first()

        if not employee:
            return Response(
                {"error": "Xodim topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        if not employee.check_pin(pin):
            logger.warning(f"Noto'g'ri PIN kiritildi: {employee.phone}")
            return Response(
                {"error": "PIN kod noto'g'ri"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = employee.user
        if not user:
            username = employee.phone.replace('+', '')
            user, _ = User.objects.get_or_create(username=username)
            employee.user = user
            employee.save()

        token, _ = Token.objects.get_or_create(user=user)
        employee.last_login = timezone.now()
        employee.save(update_fields=['last_login', 'updated_at'])

        serializer = EmployeeSerializer(employee)
        data = serializer.data
        logger.info(f"Foydalanuvchi tizimga kirdi (PIN): {employee.name} ({employee.phone})")
        return Response({
            "token": token.key,
            "user": data,
            "employee": data,
        })

class SetPinView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        employee_id = request.data.get('employee_id') or request.data.get('employee')
        quick_pin = request.data.get('quick_pin') or request.data.get('pin_code') or request.data.get('pin')
        confirm_pin = request.data.get('confirm_pin')

        employee = None
        if employee_id:
            employee = Employee.objects.filter(id=employee_id).first()
        elif request.user and request.user.is_authenticated:
            employee = getattr(request.user, 'employee_profile', None)

        if not employee:
            phone = request.data.get('phone')
            if phone:
                employee = Employee.objects.filter(phone__icontains=normalize_phone(phone)).first()

        if not employee:
            return Response({"error": "Xodim topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        if not quick_pin:
            return Response({"error": "PIN kod kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)

        if confirm_pin and str(quick_pin).strip() != str(confirm_pin).strip():
            return Response({"error": "PIN kodlar bir-biriga mos kelmadi"}, status=status.HTTP_400_BAD_REQUEST)

        employee.set_pin(str(quick_pin).strip())
        logger.info(f"PIN kod yangilandi: {employee.name} ({employee.phone})")
        return Response({
            "status": "success",
            "message": "PIN kod muvaffaqiyatli o'rnatildi",
            "pin_is_set": True
        })

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = getattr(request.user, 'employee_profile', None)
        if employee:
            serializer = EmployeeSerializer(employee)
            return Response(serializer.data)

        return Response({"error": "Xodim profili topilmadi"}, status=status.HTTP_404_NOT_FOUND)

class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if request.user and request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()
        return Response({"status": "success", "message": "Tizimdan chiqildi"})

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().select_related('role', 'branch', 'user').prefetch_related('permissions_list', 'role__module_permissions')
    serializer_class = EmployeeSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['branch', 'role', 'is_active']
    search_fields = ['name', 'phone']
    ordering_fields = ['id', 'name', 'created_at']

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all().prefetch_related('module_permissions')
    serializer_class = RoleSerializer
    permission_classes = [AllowAny]
    search_fields = ['name']

class RoleModulePermissionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        role_id = request.query_params.get('role')
        if role_id:
            perms = RoleModulePermission.objects.filter(role_id=role_id)
        else:
            perms = RoleModulePermission.objects.all()
        serializer = RoleModulePermissionSerializer(perms, many=True)
        return Response(serializer.data)

    def post(self, request):
        role_id = request.data.get('role')
        permissions = request.data.get('permissions', [])
        
        if not role_id:
            return Response({"error": "Rol ID kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)
        
        role = Role.objects.filter(id=role_id).first()
        if not role:
            return Response({"error": "Rol topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        for p in permissions:
            module = p.get('module')
            if not module:
                continue
            obj, _ = RoleModulePermission.objects.get_or_create(role=role, module=module)
            obj.can_view = p.get('can_view', p.get('view', obj.can_view))
            obj.can_create = p.get('can_create', p.get('create', obj.can_create))
            obj.can_edit = p.get('can_edit', p.get('edit', obj.can_edit))
            obj.can_delete = p.get('can_delete', p.get('delete', obj.can_delete))
            obj.save()

        updated_perms = RoleModulePermission.objects.filter(role=role)
        serializer = RoleModulePermissionSerializer(updated_perms, many=True)
        return Response(serializer.data)

class EmployeePermissionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        emp_id = request.query_params.get('employee')
        if emp_id:
            perms = EmployeePermission.objects.filter(employee_id=emp_id)
        else:
            perms = EmployeePermission.objects.all()
        serializer = EmployeePermissionSerializer(perms, many=True)
        return Response(serializer.data)

    def post(self, request):
        emp_id = request.data.get('employee')
        permissions = request.data.get('permissions', [])

        if not emp_id:
            return Response({"error": "Xodim ID kiritilishi shart"}, status=status.HTTP_400_BAD_REQUEST)

        emp = Employee.objects.filter(id=emp_id).first()
        if not emp:
            return Response({"error": "Xodim topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        for p in permissions:
            module = p.get('module')
            action = p.get('action', 'view')
            val = p.get('value', True)
            if not module:
                continue
            obj, _ = EmployeePermission.objects.get_or_create(employee=emp, module=module, action=action)
            obj.value = bool(val)
            if 'can_payment' in p: obj.can_payment = bool(p['can_payment'])
            if 'can_discount' in p: obj.can_discount = bool(p['can_discount'])
            if 'can_cancel_order' in p: obj.can_cancel_order = bool(p['can_cancel_order'])
            if 'can_income' in p: obj.can_income = bool(p['can_income'])
            obj.save()

        updated = EmployeePermission.objects.filter(employee=emp)
        serializer = EmployeePermissionSerializer(updated, many=True)
        return Response(serializer.data)

class SalarySchemeViewSet(viewsets.ModelViewSet):
    queryset = SalaryScheme.objects.all()
    serializer_class = SalarySchemeSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['employee', 'salary_type']

class SalaryRecordViewSet(viewsets.ModelViewSet):
    queryset = SalaryRecord.objects.all().select_related('employee')
    serializer_class = SalaryRecordSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['employee', 'month', 'status', 'salary_type']
    ordering_fields = ['id', 'created_at', 'amount']

class SalarySimulateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        salary_type = request.data.get('type') or request.data.get('salary_type') or 'fiksa'
        params = request.data.get('params') or {}
        metrics = request.data.get('metrics') or {}

        def clean_dec(val, default=0):
            if val is None or val == '':
                return Decimal(str(default))
            if isinstance(val, (int, float, Decimal)):
                return Decimal(str(val))
            s = str(val).replace(' ', '').replace(',', '.').replace("so'm", '').replace('UZS', '').strip()
            try:
                return Decimal(s)
            except Exception:
                return Decimal(str(default))

        orders_total = clean_dec(metrics.get('ordersTotal') or metrics.get('orders_total'), 0)
        hours_worked = clean_dec(metrics.get('hoursWorked') or metrics.get('hours_worked'), 0)
        shifts_count = clean_dec(metrics.get('shiftsCount') or metrics.get('shifts_count'), 0)

        calculated = Decimal('0.0')

        if salary_type in ['fiksa', 'fixed', 'monthly']:
            summa = clean_dec(params.get('summa') or params.get('salary_amount') or params.get('amount') or params.get('baza_summa'))
            calculated = summa
        elif salary_type in ['foizli', 'percentage', 'percent']:
            foiz = clean_dec(params.get('foiz') or params.get('percent') or params.get('rate'))
            calculated = (orders_total * foiz / Decimal('100'))
        elif salary_type in ['soatlik', 'hourly']:
            stavka = clean_dec(params.get('stavka') or params.get('hourly_rate') or params.get('soat_narxi'))
            calculated = hours_worked * stavka
        elif salary_type in ['fiksa_foiz', 'mixed', 'fixed_percent']:
            baza = clean_dec(params.get('baza_summa') or params.get('summa') or params.get('base_amount'))
            foiz = clean_dec(params.get('qoshimcha_foiz') or params.get('foiz') or params.get('percent'))
            calculated = baza + (orders_total * foiz / Decimal('100'))
        elif salary_type in ['smena', 'shift', 'kunlik']:
            smena_narxi = clean_dec(params.get('smena_narxi') or params.get('shift_rate') or params.get('kunlik'))
            calculated = shifts_count * smena_narxi
        elif salary_type == 'ball':
            ball_qiymati = clean_dec(params.get('ball_qiymati'), 1)
            bazaviy_ball = clean_dec(params.get('bazaviy_ball'), 0)
            bazaviy_summa = clean_dec(params.get('bazaviy_summa'), 0)
            bonus_bir_ball = clean_dec(params.get('bonus_bir_ball'), 0)

            if ball_qiymati > 0:
                jami_ball = int(orders_total // ball_qiymati)
                if jami_ball <= bazaviy_ball:
                    calculated = bazaviy_summa
                else:
                    excess = jami_ball - bazaviy_ball
                    calculated = bazaviy_summa + (excess * bonus_bir_ball)
            else:
                calculated = bazaviy_summa

        return Response({
            "type": salary_type,
            "calculated_amount": round(float(calculated)),
            "params": params,
            "metrics": metrics
        })

