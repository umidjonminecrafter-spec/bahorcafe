from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet,
    OrderItemViewSet,
    CheckoutPrintView,
    ReceiptPrintView,
    PaymentStartView,
    OrderReportsView
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='orders')
router.register(r'order-items', OrderItemViewSet, basename='order-items')

urlpatterns = [
    path('checkout-print/', CheckoutPrintView.as_view(), name='checkout-print'),
    path('reports/', OrderReportsView.as_view(), name='order-reports'),
    path('', include(router.urls)),
]
