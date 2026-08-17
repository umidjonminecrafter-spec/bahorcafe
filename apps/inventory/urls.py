from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WarehouseViewSet,
    InventoryCategoryViewSet,
    UnitViewSet,
    SupplierViewSet,
    InventoryProductViewSet,
    PurchaseViewSet,
    WriteOffViewSet,
    RealizationViewSet,
    InventoryStockHistoryViewSet,
    EdiImportView,
    ExcelProductImportView,
    ExcelPurchaseImportView
)

router = DefaultRouter()
router.register(r'ombor', WarehouseViewSet, basename='ombor')
router.register(r'warehouses', WarehouseViewSet, basename='warehouses')
router.register(r'kategoriya', InventoryCategoryViewSet, basename='kategoriya')
router.register(r'categories', InventoryCategoryViewSet, basename='categories')
router.register(r'unit', UnitViewSet, basename='unit')
router.register(r'suppliers', SupplierViewSet, basename='suppliers')
router.register(r'products', InventoryProductViewSet, basename='products')
router.register(r'purchases', PurchaseViewSet, basename='purchases')
router.register(r'kirim', PurchaseViewSet, basename='kirim')
router.register(r'chiqim', WriteOffViewSet, basename='chiqim')
router.register(r'realizations', RealizationViewSet, basename='realizations')
router.register(r'tarix', InventoryStockHistoryViewSet, basename='tarix')

urlpatterns = [
    path('edi-import/', EdiImportView.as_view(), name='edi-import'),
    path('import-excel/', ExcelProductImportView.as_view(), name='inventory-import-excel'),
    path('products/import/', ExcelProductImportView.as_view(), name='inventory-products-import'),
    path('products/import-excel/', ExcelProductImportView.as_view(), name='inventory-products-import-excel'),
    path('purchases/import-excel/', ExcelPurchaseImportView.as_view(), name='inventory-purchases-import-excel'),
    path('kirim/import-excel/', ExcelPurchaseImportView.as_view(), name='inventory-kirim-import-excel'),
    path('', include(router.urls)),
]
