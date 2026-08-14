from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView,
    PinLoginView,
    SetPinView,
    MeView,
    LogoutView,
    EmployeeViewSet,
    RoleViewSet,
    RoleModulePermissionView,
    EmployeePermissionView,
    SalarySchemeViewSet,
    SalaryRecordViewSet,
    SalarySimulateView
)

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet, basename='employees')
router.register(r'roles', RoleViewSet, basename='roles')
router.register(r'salary-schemes', SalarySchemeViewSet, basename='salary-schemes')
router.register(r'salary-records', SalaryRecordViewSet, basename='salary-records')

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/pin-login/', PinLoginView.as_view(), name='pin-login'),
    path('auth/set-pin/', SetPinView.as_view(), name='set-pin'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    path('role-permissions/', RoleModulePermissionView.as_view(), name='role-permissions'),
    path('role-module-permissions/', RoleModulePermissionView.as_view(), name='role-module-permissions'),
    path('permissions/', EmployeePermissionView.as_view(), name='employee-permissions'),
    path('salary/simulate/', SalarySimulateView.as_view(), name='salary-simulate'),

    path('', include(router.urls)),
]
