from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TableViewSet,
    TablePartViewSet,
    TableLayoutView,
    ProductCategoryViewSet,
    ProductViewSet,
    ProductIngredientViewSet
)

router = DefaultRouter()
router.register(r'table', TableViewSet, basename='table')
router.register(r'table-part', TablePartViewSet, basename='table-part')
router.register(r'category', ProductCategoryViewSet, basename='category')
router.register(r'product', ProductViewSet, basename='product')
router.register(r'product-ingredients', ProductIngredientViewSet, basename='product-ingredients')

urlpatterns = [
    path('table-layout/', TableLayoutView.as_view(), name='table-layout'),
    path('', include(router.urls)),
]
