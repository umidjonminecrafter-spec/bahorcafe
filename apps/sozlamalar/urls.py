from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BranchViewSet,
    RestaurantSettingsView,
    TaxSettingsView,
    CheckSettingsView,
    OrderFlowSettingsView
)

router = DefaultRouter()
router.register(r'branches', BranchViewSet, basename='branches')

urlpatterns = [
    path('restaurant-settings/', RestaurantSettingsView.as_view(), name='restaurant-settings'),
    path('tax-settings/', TaxSettingsView.as_view(), name='tax-settings'),
    path('check-settings/', CheckSettingsView.as_view(), name='check-settings'),
    path('order-flow/', OrderFlowSettingsView.as_view(), name='order-flow'),
    path('order-flow-settings/', OrderFlowSettingsView.as_view(), name='order-flow-settings'),
    path('', include(router.urls)),
]
