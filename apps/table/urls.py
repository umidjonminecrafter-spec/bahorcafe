from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TableViewSet,
    TablePartViewSet,
    TableLayoutView,
    ProductCategoryViewSet,
    ProductViewSet,
    ProductIngredientViewSet,
    ExcelMenuImportView
)

router = DefaultRouter()
router.register(r'table', TableViewSet, basename='table')
router.register(r'table-part', TablePartViewSet, basename='table-part')
router.register(r'category', ProductCategoryViewSet, basename='category')
router.register(r'product', ProductViewSet, basename='product')
router.register(r'products', ProductViewSet, basename='products')
router.register(r'product-ingredients', ProductIngredientViewSet, basename='product-ingredients')

urlpatterns = [
    path('table-layout/', TableLayoutView.as_view(), name='table-layout'),
    path('products/import/', ExcelMenuImportView.as_view(), name='table-products-import'),
    path('products/import-excel/', ExcelMenuImportView.as_view(), name='table-products-import-excel'),
    path('product/import/', ExcelMenuImportView.as_view(), name='table-product-import'),
    path('import-excel/', ExcelMenuImportView.as_view(), name='table-import-excel'),
    path('', include(router.urls)),
]
