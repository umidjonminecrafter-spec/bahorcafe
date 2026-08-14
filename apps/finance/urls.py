from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FinanceAccountViewSet,
    FinanceCategoryViewSet,
    FinanceTransactionViewSet,
    FinanceMonitoringView
)

router = DefaultRouter()
router.register(r'accounts', FinanceAccountViewSet, basename='accounts')
router.register(r'categories', FinanceCategoryViewSet, basename='categories')
router.register(r'transactions', FinanceTransactionViewSet, basename='transactions')

urlpatterns = [
    path('monitoring/', FinanceMonitoringView.as_view(), name='monitoring'),
    path('', include(router.urls)),
]
