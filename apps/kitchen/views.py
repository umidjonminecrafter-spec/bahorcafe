from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db.models import Sum, Count, Avg, F, Q
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from .models import Department, SemiProduct, SemiProductIngredient
from .serializers import DepartmentSerializer, SemiProductSerializer
from apps.table.models import Product, ProductCategory, ProductIngredient, Table
from apps.table.serializers import ProductSerializer, ProductCategorySerializer, ProductIngredientSerializer
from apps.order.models import Order, OrderItem
from apps.inventory.models import InventoryProduct

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['filial', 'ombor', 'is_active']
    search_fields = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('filial')
        if branch_id:
            qs = qs.filter(filial_id=branch_id)
        return qs

class SemiProductViewSet(viewsets.ModelViewSet):
    queryset = SemiProduct.objects.all().select_related('category').prefetch_related('ingredients', 'ingredients__ingredient')
    serializer_class = SemiProductSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name']

class KitchenFoodsViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category', 'department').prefetch_related('ingredients')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category', 'department', 'is_active']
    search_fields = ['name', 'mxik']
    ordering_fields = ['id', 'name', 'price']

class KitchenCategoriesViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [AllowAny]
    search_fields = ['name']

class KitchenRecipesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        ingredients = ProductIngredient.objects.all().select_related('product', 'maxsulot')
        serializer = ProductIngredientSerializer(ingredients, many=True)
        return Response(serializer.data)

class DashboardLiveView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        branch_id = request.query_params.get('branch_id') or request.query_params.get('branch')
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        orders_qs = Order.objects.all()
        if branch_id:
            orders_qs = orders_qs.filter(branch_id=branch_id)

        today_orders = orders_qs.filter(created_at__gte=today_start)
        today_paid = today_orders.filter(status='paid')

        today_revenue = today_paid.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.0')
        today_cost = OrderItem.objects.filter(order__in=today_paid).aggregate(total=Sum(F('qty') * F('cost_price')))['total'] or Decimal('0.0')
        today_profit = max(Decimal('0.0'), today_revenue - today_cost)
        today_count = today_paid.count()
        today_avg = (today_revenue / today_count) if today_count > 0 else Decimal('0.0')

        # Kitchen cooking count
        cooking_count = OrderItem.objects.filter(status='cooking').count()
        # Busy tables
        tables_qs = Table.objects.all()
        if branch_id:
            tables_qs = tables_qs.filter(branch_id=branch_id)
        busy_tables = tables_qs.filter(is_busy=True).count()

        # Last 7 days revenue
        weekly_data = []
        for i in range(6, -1, -1):
            day_dt = now - timedelta(days=i)
            d_start = day_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            d_end = day_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            d_rev = orders_qs.filter(status='paid', paid_at__range=(d_start, d_end)).aggregate(t=Sum('total_amount'))['t'] or 0
            day_name = day_dt.strftime('%a')
            weekly_data.append({
                "day": day_name,
                "date": day_dt.strftime('%Y-%m-%d'),
                "tushum": float(d_rev)
            })

        # Top 5 products
        top_items = (
            OrderItem.objects.filter(order__in=today_paid)
            .values('product__name')
            .annotate(qty=Sum('qty'), total=Sum('total_price'))
            .order_by('-qty')[:5]
        )
        top_foods = [{"nomi": it['product__name'] or 'Taom', "miqdor": float(it['qty']), "summa": float(it['total'])} for it in top_items]

        # Category shares
        cat_items = (
            OrderItem.objects.filter(order__in=today_paid)
            .values('product__category__name')
            .annotate(total=Sum('total_price'))
            .order_by('-total')
        )
        category_shares = [{"kategoriya": it['product__category__name'] or 'Boshqa', "summa": float(it['total'])} for it in cat_items]

        # Order types
        type_counts = {
            "dine_in": today_orders.filter(type='dine_in').count(),
            "takeaway": today_orders.filter(type='takeaway').count(),
            "delivery": today_orders.filter(type='delivery').count(),
        }

        return Response({
            "jonli_holat": {
                "oshxona_tayyorlanmoqda": cooking_count,
                "oshxona_kechikkan": max(0, cooking_count - 3),
                "band_stollar_ochiq": busy_tables,
                "bugungi_pul_tushumi": float(today_revenue),
                "bugungi_foyda": float(today_profit),
                "bugungi_buyurtmalar": today_count,
                "ortacha_chek": float(today_avg),
            },
            "haftalik_tushum": weekly_data,
            "top_taomlar": top_foods,
            "kategoriya_ulushi": category_shares,
            "buyurtma_turlari": type_counts,
            "updated_at": now.isoformat()
        })

class SyncStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        sana_str = now.strftime('%d %b, %Y')
        vaqt_str = now.strftime('%H:%M:%S')

        return Response({
            "bo_limlar": {
                "dashboard": {"holat": "Faol", "sana": sana_str, "vaqt": vaqt_str, "url": "/kitchen/dashboard/"},
                "ombor": {"holat": "Faol", "sana": sana_str, "vaqt": vaqt_str, "url": "/inventory/products/"},
                "sozlamalar": {"holat": "Faol", "sana": sana_str, "vaqt": vaqt_str, "url": "/sozlamalar/restaurant-settings/"},
                "menyu": {"holat": "Faol", "sana": sana_str, "vaqt": vaqt_str, "url": "/table/product/"},
                "xodimlar": {"holat": "Faol", "sana": sana_str, "vaqt": vaqt_str, "url": "/employee/employees/"},
                "kassa": {"holat": "Faol", "sana": sana_str, "vaqt": vaqt_str, "url": "/order/orders/"},
                "hisobotlar": {"holat": "Faol", "sana": sana_str, "vaqt": vaqt_str, "url": "/kitchen/umumiy-hisobot/"},
            }
        })

class UmumiyHisobotView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        branch_id = params.get('branch_id') or params.get('branch') or params.get('filial')
        from_date = params.get('from_date') or params.get('from') or params.get('start_date')
        to_date = params.get('to_date') or params.get('to') or params.get('end_date')
        group_by = params.get('group_by', 'kun')

        orders = Order.objects.filter(status__in=['paid', 'closed', 'completed'])
        if branch_id:
            orders = orders.filter(branch_id=branch_id)
        if from_date:
            orders = orders.filter(created_at__date__gte=from_date)
        if to_date:
            orders = orders.filter(created_at__date__lte=to_date)

        total_revenue = orders.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0')
        order_items = OrderItem.objects.filter(order__in=orders)
        total_cost = order_items.aggregate(s=Sum(F('qty') * F('cost_price')))['s'] or Decimal('0.0')
        total_profit = max(Decimal('0.0'), total_revenue - total_cost)
        total_checks = orders.count()
        avg_check = (total_revenue / total_checks) if total_checks > 0 else Decimal('0.0')

        # Dinamika breakdown by date and cashier/waiter
        dinamika = []
        date_cashier_groups = (
            orders.values('created_at__date', 'assigned_waiter__name')
            .annotate(
                tushum=Sum('total_amount'),
                soni=Count('id')
            )
            .order_by('created_at__date')
        )
        for g in date_cashier_groups:
            d_date = str(g['created_at__date'])
            k_name = g['assigned_waiter__name'] or 'Admin'
            d_tushum = float(g['tushum'] or 0)
            d_cnt = g['soni'] or 1
            d_items = OrderItem.objects.filter(
                order__in=orders,
                order__created_at__date=g['created_at__date'],
                order__assigned_waiter__name=g['assigned_waiter__name']
            )
            d_cost = float(d_items.aggregate(s=Sum(F('qty') * F('cost_price')))['s'] or 0)
            d_profit = max(0.0, d_tushum - d_cost)
            dinamika.append({
                "sana": d_date,
                "date": d_date,
                "kun": d_date,
                "label": d_date,
                "key": d_date,
                "kassa": k_name,
                "kassa_nomi": k_name,
                "name": k_name,
                "tushum": d_tushum,
                "total": d_tushum,
                "jami_tushum": d_tushum,
                "value": d_tushum,
                "foyda": d_profit,
                "profit": d_profit,
                "tannarx": d_cost,
                "soni": d_cnt,
                "count": d_cnt,
                "savdolar": d_cnt,
                "cheklar": d_cnt,
                "ortacha_chek": round(d_tushum / d_cnt, 2) if d_cnt > 0 else 0
            })

        # Kassalar statistikasi
        kassalar_stats = (
            orders.values('assigned_waiter__id', 'assigned_waiter__name')
            .annotate(
                tushum=Sum('total_amount'),
                soni=Count('id')
            )
            .order_by('-tushum')
        )
        kassalar_statistikasi = []
        for ks in kassalar_stats:
            k_name = ks['assigned_waiter__name'] or 'Admin'
            k_tushum = float(ks['tushum'] or 0)
            k_cnt = ks['soni'] or 1
            k_items = OrderItem.objects.filter(order__in=orders, order__assigned_waiter__name=ks['assigned_waiter__name'])
            k_cost = float(k_items.aggregate(s=Sum(F('qty') * F('cost_price')))['s'] or 0)
            k_profit = max(0.0, k_tushum - k_cost)
            kassalar_statistikasi.append({
                "nomi": k_name,
                "kassa_nomi": k_name,
                "name": k_name,
                "kassa": k_name,
                "tushum": k_tushum,
                "total": k_tushum,
                "value": k_tushum,
                "foyda": k_profit,
                "profit": k_profit,
                "soni": k_cnt,
                "count": k_cnt,
                "savdolar": k_cnt,
                "cheklar": k_cnt,
                "ortacha_chek": round(k_tushum / k_cnt, 2) if k_cnt > 0 else 0
            })

        # Day by day breakdown (davrlar) for backward compatibility
        davrlar = []
        date_groups = (
            orders.values('created_at__date')
            .annotate(
                tushum=Sum('total_amount'),
                cheklar=Count('id')
            )
            .order_by('created_at__date')
        )
        for g in date_groups:
            d_date = str(g['created_at__date'])
            d_rev = float(g['tushum'] or 0)
            d_items = OrderItem.objects.filter(order__in=orders, order__created_at__date=g['created_at__date'])
            d_cost = float(d_items.aggregate(s=Sum(F('qty') * F('cost_price')))['s'] or 0)
            d_profit = max(0.0, d_rev - d_cost)
            d_cnt = g['cheklar'] or 1
            davrlar.append({
                "davr": d_date,
                "sana": d_date,
                "tushum": d_rev,
                "tannarx": d_cost,
                "foyda": d_profit,
                "cheklar": d_cnt,
                "ortacha_chek": round(d_rev / d_cnt, 2),
            })

        return Response({
            "jami_tushum": float(total_revenue),
            "jami_tannarx": float(total_cost),
            "jami_foyda": float(total_profit),
            "jami_cheklar": total_checks,
            "ortacha_chek": round(float(avg_check), 2),
            "dinamika": dinamika,
            "kassalar_statistikasi": kassalar_statistikasi,
            "summary": {
                "jami_tushum": float(total_revenue),
                "jami_tannarx": float(total_cost),
                "jami_foyda": float(total_profit),
                "jami_cheklar": total_checks,
                "ortacha_chek": round(float(avg_check), 2),
            },
            "davrlar": davrlar
        })

class SotuvHisobotiView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        branch_id = params.get('branch_id') or params.get('branch') or params.get('filial')
        from_date = params.get('from_date') or params.get('from') or params.get('start_date')
        to_date = params.get('to_date') or params.get('to') or params.get('end_date')

        orders = Order.objects.filter(status__in=['paid', 'closed', 'completed'])
        if branch_id:
            orders = orders.filter(branch_id=branch_id)
        if from_date:
            orders = orders.filter(created_at__date__gte=from_date)
        if to_date:
            orders = orders.filter(created_at__date__lte=to_date)

        items = (
            OrderItem.objects.filter(order__in=orders)
            .values(
                'product__id',
                'product__name',
                'product__category__name',
                'product__mxik',
                'order__created_at__date',
                'order__assigned_waiter__name'
            )
            .annotate(
                miqdor=Sum('qty'),
                tushum=Sum('total_price'),
                tannarx_jami=Sum(F('qty') * F('cost_price'))
            )
            .order_by('-tushum')
        )

        results = []
        for it in items:
            tushum = it['tushum'] or Decimal('0.0')
            tannarx = it['tannarx_jami'] or Decimal('0.0')
            foyda = max(Decimal('0.0'), tushum - tannarx)
            marja = ((foyda / tushum) * 100) if tushum > 0 else Decimal('0.0')
            p_name = it['product__name'] or 'Taom'
            c_name = it['product__category__name'] or 'Umumiy'
            sana_str = str(it['order__created_at__date']) if it.get('order__created_at__date') else ""
            kassa_name = it.get('order__assigned_waiter__name') or 'Asosiy Kassa'

            results.append({
                "sana": sana_str,
                "product_id": it['product__id'],
                "product_name": p_name,
                "nomi": p_name,
                "category": c_name,
                "kategoriya": c_name,
                "artikul": it.get('product__mxik') or str(it['product__id'] or "—"),
                "kassa": kassa_name,
                "miqdor": float(it['miqdor'] or 0),
                "qty": float(it['miqdor'] or 0),
                "tushum": float(tushum),
                "sofTushum": float(tushum),
                "tannarx": float(tannarx),
                "foyda": float(foyda),
                "chegirma": 0,
                "qaytarish": 0,
                "marja": round(float(marja), 1),
                "marja_foiz": round(float(marja), 1)
            })

        return Response(results)

class XodimlarHisobotiView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        branch_id = params.get('branch_id') or params.get('branch') or params.get('filial')
        from_date = params.get('from_date') or params.get('from') or params.get('start_date')
        to_date = params.get('to_date') or params.get('to') or params.get('end_date')

        orders = Order.objects.filter(status__in=['paid', 'closed', 'completed'])
        if branch_id:
            orders = orders.filter(branch_id=branch_id)
        if from_date:
            orders = orders.filter(created_at__date__gte=from_date)
        if to_date:
            orders = orders.filter(created_at__date__lte=to_date)

        waiter_stats = (
            orders.values(
                'assigned_waiter__id',
                'assigned_waiter__name',
                'assigned_waiter__role__name',
                'created_at__date'
            )
            .annotate(
                buyurtmalar_soni=Count('id'),
                mehmonlar_soni=Sum('guests_count'),
                jami_tushum=Sum('total_amount'),
                xizmat_haqqi=Sum('service_amount')
            )
            .order_by('-created_at__date', '-jami_tushum')
        )

        results = []
        for ws in waiter_stats:
            w_name = ws['assigned_waiter__name'] or 'Admin'
            cnt = ws['buyurtmalar_soni'] or 1
            tushum = ws['jami_tushum'] or Decimal('0.0')
            sana_str = str(ws['created_at__date']) if ws.get('created_at__date') else "—"

            results.append({
                "sana": sana_str,
                "xodim_id": ws['assigned_waiter__id'],
                "xodim_name": w_name,
                "xodim": w_name,
                "sotuvchi": w_name,
                "kassa": w_name,
                "lavozim": ws['assigned_waiter__role__name'] or 'Ofitsiant',
                "buyurtmalar_soni": cnt,
                "chek_soni": cnt,
                "mehmonlar_soni": ws['mehmonlar_soni'] or 0,
                "tushum": float(tushum),
                "jami_tushum": float(tushum),
                "xizmat_haqqi": float(ws['xizmat_haqqi'] or 0),
                "chegirma": 0,
                "qaytarish": 0,
                "qaytarish_soni": 0,
                "ortacha_chek": round(float(tushum / cnt), 2)
            })

        return Response(results)

class AbcAnalysisView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        params = request.query_params
        branch_id = params.get('branch_id') or params.get('branch') or params.get('filial')
        from_date = params.get('from_date') or params.get('from') or params.get('start_date')
        to_date = params.get('to_date') or params.get('to') or params.get('end_date')

        orders = Order.objects.filter(status__in=['paid', 'closed', 'completed'])
        if branch_id:
            orders = orders.filter(branch_id=branch_id)
        if from_date:
            orders = orders.filter(created_at__date__gte=from_date)
        if to_date:
            orders = orders.filter(created_at__date__lte=to_date)

        items = (
            OrderItem.objects.filter(order__in=orders)
            .values('product__id', 'product__name', 'product__category__name')
            .annotate(
                miqdor=Sum('qty'),
                tushum=Sum('total_price'),
                tannarx_jami=Sum(F('qty') * F('cost_price'))
            )
            .order_by('-tushum')
        )

        total_all_revenue = sum([Decimal(str(it['tushum'] or 0)) for it in items], Decimal('0.0'))

        results = []
        cumulative_rev = Decimal('0.0')

        for it in items:
            tushum = Decimal(str(it['tushum'] or 0))
            tannarx = it['tannarx_jami'] or Decimal('0.0')
            foyda = max(Decimal('0.0'), tushum - tannarx)
            cumulative_rev += tushum
            share_percent = ((tushum / total_all_revenue) * 100) if total_all_revenue > 0 else Decimal('0.0')
            cum_percent = ((cumulative_rev / total_all_revenue) * 100) if total_all_revenue > 0 else Decimal('0.0')

            if cum_percent <= 80:
                abc_class = 'A'
            elif cum_percent <= 95:
                abc_class = 'B'
            else:
                abc_class = 'C'

            p_name = it['product__name'] or 'Taom'
            c_name = it['product__category__name'] or 'Umumiy'

            results.append({
                "product_id": it['product__id'],
                "product_name": p_name,
                "nomi": p_name,
                "category": c_name,
                "kategoriya": abc_class,
                "kategoriya_abc": abc_class,
                "mahsulot_kategoriya": c_name,
                "kategoriya_nomi": c_name,
                "miqdor": float(it['miqdor'] or 0),
                "sotuv": float(it['miqdor'] or 0),
                "tushum": float(tushum),
                "tannarx": float(tannarx),
                "foyda": float(foyda),
                "ulush_foiz": round(float(share_percent), 2),
                "kumulyativ_foiz": round(float(cum_percent), 2),
                "sinf": abc_class,
                "abc_class": abc_class
            })

        return Response(results)
