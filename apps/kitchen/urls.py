from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet,
    SemiProductViewSet,
    KitchenFoodsViewSet,
    KitchenCategoriesViewSet,
    KitchenRecipesView,
    DashboardLiveView,
    SyncStatusView,
    UmumiyHisobotView,
    SotuvHisobotiView,
    XodimlarHisobotiView,
    AbcAnalysisView
)
from apps.table.views import ExcelMenuImportView

router = DefaultRouter()
router.register(r'departments', DepartmentViewSet, basename='departments')
router.register(r'semi-products', SemiProductViewSet, basename='semi-products')
router.register(r'foods', KitchenFoodsViewSet, basename='foods')
router.register(r'categories', KitchenCategoriesViewSet, basename='categories')

urlpatterns = [
    path('recipes/', KitchenRecipesView.as_view(), name='recipes'),
    path('dashboard/', DashboardLiveView.as_view(), name='dashboard-live'),
    path('dashboard-live/', DashboardLiveView.as_view(), name='dashboard-live-alias'),
    path('sync-status/', SyncStatusView.as_view(), name='sync-status'),
    path('umumiy-hisobot/', UmumiyHisobotView.as_view(), name='umumiy-hisobot'),
    path('sotuv-hisoboti/', SotuvHisobotiView.as_view(), name='sotuv-hisoboti'),
    path('xodimlar-hisoboti/', XodimlarHisobotiView.as_view(), name='xodimlar-hisoboti'),
    path('abc-analysis/', AbcAnalysisView.as_view(), name='abc-analysis'),
    path('foods/import/', ExcelMenuImportView.as_view(), name='kitchen-foods-import'),
    path('foods/import-excel/', ExcelMenuImportView.as_view(), name='kitchen-foods-import-excel'),
    path('import-excel/', ExcelMenuImportView.as_view(), name='kitchen-import-excel'),
    path('', include(router.urls)),
]
