from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.sozlamalar.views import OrderFlowSettingsView, CheckSettingsView
from apps.order.views import ReceiptPrintView, PaymentStartView
from apps.finance.views import FinanceTransactionViewSet, FinanceAccountViewSet, FinanceMonitoringView
from rest_framework.routers import DefaultRouter

# Additional alias routers
order_alias_router = DefaultRouter()
order_alias_router.register(r'transactions', FinanceTransactionViewSet, basename='order-transactions')

inv_alias_router = DefaultRouter()
inv_alias_router.register(r'accounts', FinanceAccountViewSet, basename='inv-accounts')
inv_alias_router.register(r'transactions', FinanceTransactionViewSet, basename='inv-transactions')

urlpatterns = [
    path('admin/', admin.site.urls),

    # App URLs
    path('employee/', include('apps.employee.urls')),
    path('sozlamalar/', include('apps.sozlamalar.urls')),
    path('table/', include('apps.table.urls')),
    path('kitchen/', include('apps.kitchen.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('order/', include('apps.order.urls')),
    path('finance/', include('apps.finance.urls')),

    # Special Direct Aliases used by Frontend
    path('order-flow/', OrderFlowSettingsView.as_view(), name='direct-order-flow'),
    path('order/check-settings/', CheckSettingsView.as_view(), name='order-check-settings'),
    path('order/finance-monitoring/', FinanceMonitoringView.as_view(), name='order-finance-monitoring'),
    path('inventory/monitoring/', FinanceMonitoringView.as_view(), name='inv-monitoring'),
    path('receipts/print/', ReceiptPrintView.as_view(), name='direct-receipts-print'),
    path('payments/start', PaymentStartView.as_view(), name='direct-payments-start'),
    path('payments/start/', PaymentStartView.as_view(), name='direct-payments-start-slash'),

    # Direct nested alias routers for /order/ and /inventory/
    path('order/', include(order_alias_router.urls)),
    path('inventory/', include(inv_alias_router.urls)),

    # API Documentation (Swagger / OpenAPI / ReDoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
