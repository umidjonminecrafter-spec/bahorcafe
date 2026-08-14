from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger('bahor_app')

from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer
from apps.table.models import Table, Product, ProductIngredient
from apps.inventory.models import InventoryProduct, InventoryStockHistory
from apps.finance.models import FinanceTransaction, FinanceAccount, FinanceCategory
from apps.sozlamalar.models import ReceiptSettings, TaxSettings, Branch

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().select_related('table', 'branch', 'assigned_waiter').prefetch_related('items', 'items__product', 'items__product__department')
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['branch', 'table', 'status', 'type', 'assigned_waiter']
    search_fields = ['number', 'note']
    ordering_fields = ['id', 'number', 'created_at', 'total_amount']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        branch_id = params.get('branch_id') or params.get('branch') or params.get('filial')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        table_id = params.get('table') or params.get('table_id')
        if table_id:
            qs = qs.filter(table_id=table_id)

        status_param = params.get('status')
        if status_param:
            if status_param in ['tolangan', 'paid']:
                qs = qs.filter(status__in=['paid', 'closed', 'completed'])
            elif status_param in ['ochiq', 'open']:
                qs = qs.filter(status__in=['open', 'ready', 'cooking', 'sent_to_kitchen'])
            elif status_param in ['bekor_qilingan', 'cancelled', 'canceled']:
                qs = qs.filter(status__in=['cancelled', 'canceled'])
            else:
                qs = qs.filter(status=status_param)

        type_param = params.get('type') or params.get('order_type')
        if type_param:
            qs = qs.filter(type=type_param)

        waiter_id = params.get('assigned_waiter') or params.get('waiter_id') or params.get('employee_id')
        if waiter_id:
            qs = qs.filter(assigned_waiter_id=waiter_id)

        start_date = params.get('start_date') or params.get('from_date') or params.get('from')
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)

        end_date = params.get('end_date') or params.get('to_date') or params.get('to')
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        search_query = params.get('search') or params.get('q')
        if search_query:
            from django.db.models import Q
            qs = qs.filter(Q(number__icontains=search_query) | Q(note__icontains=search_query) | Q(id__icontains=search_query))

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Calculate cards statistics
        total_orders_count = queryset.count()
        paid_orders = queryset.filter(status__in=['paid', 'closed', 'completed'])
        total_revenue = paid_orders.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0')
        cancelled_count = queryset.filter(status__in=['cancelled', 'canceled']).count()
        paid_count = paid_orders.count()
        avg_check = (total_revenue / paid_count) if paid_count > 0 else Decimal('0.0')

        cards = {
            "jami_buyurtmalar": total_orders_count,
            "tushum": float(total_revenue),
            "bekor_qilingan": cancelled_count,
            "ortacha_chek": round(float(avg_check), 2)
        }

        # Build orders_table for T8 component
        orders_table = []
        for order in queryset:
            # Determine joylashuv
            if order.type == 'takeaway':
                joylashuv = "Olib ketish (Saboy)"
                stol_label = "takeaway"
            elif order.type == 'delivery':
                joylashuv = "Yetkazib berish"
                stol_label = "delivery"
            elif order.table:
                joylashuv = order.table.name
                stol_label = order.table.name
            else:
                joylashuv = "—"
                stol_label = "—"

            waiter_name = order.assigned_waiter.name if order.assigned_waiter else "Admin"
            sana_vaqt_str = timezone.localtime(order.created_at).strftime("%d.%m.%Y %H:%M") if order.created_at else "—"

            orders_table.append({
                "id": order.id,
                "buyurtma_raqami": order.number or order.id,
                "number": order.number or order.id,
                "joylashuv": joylashuv,
                "stol": stol_label,
                "ofitsiant": waiter_name,
                "assigned_waiter": order.assigned_waiter_id,
                "assigned_waiter_id": order.assigned_waiter_id,
                "mehmonlar_soni": order.guests_count or 1,
                "status": order.status,
                "sana_vaqt": sana_vaqt_str,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "summa": float(order.total_amount),
                "total_amount": float(order.total_amount),
                "type": order.type,
                "table": order.table_id,
                "note": order.note or "",
                "items": OrderItemSerializer(order.items.all(), many=True).data
            })

        # Serialized full objects for all other components (POS, Kassa, etc.)
        results_data = self.get_serializer(queryset, many=True).data

        return Response({
            "count": total_orders_count,
            "cards": cards,
            "orders_table": orders_table,
            "results": results_data
        })

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        items_data = data.pop('items_data', []) or data.pop('items', [])

        # Fetch service percent from TaxSettings if not provided
        branch_id = data.get('branch') or 1
        if 'service_percent' not in data:
            tax_set = TaxSettings.objects.filter(branch_id=branch_id).first()
            if tax_set:
                data['service_percent'] = tax_set.service_percent

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        # Mark table as busy if dine_in
        if order.table:
            order.table.status = 'busy'
            order.table.is_busy = True
            order.table.save(update_fields=['status', 'is_busy', 'updated_at'])

        for it in items_data:
            product_id = it.get('product') or it.get('product_id') or it.get('id')
            if not product_id:
                continue
            product = Product.objects.filter(id=product_id).first()
            if not product:
                continue

            qty = Decimal(str(it.get('qty') or it.get('quantity') or 1))
            unit_price = Decimal(str(it.get('unit_price') or it.get('price') or product.price))
            note = str(it.get('note') or '')

            OrderItem.objects.create(
                order=order,
                product=product,
                qty=qty,
                unit_price=unit_price,
                cost_price=product.cost_price,
                note=note,
                status='pending'
            )

        order.recalculate_totals()
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='send_to_kitchen')
    def send_to_kitchen(self, request, pk=None):
        order = self.get_object()
        order.status = 'sent_to_kitchen'
        order.save(update_fields=['status', 'updated_at'])
        order.items.filter(status='pending').update(status='cooking')
        return Response({
            "status": "success",
            "message": "Buyurtma oshxonaga yuborildi",
            "order": self.get_serializer(order).data
        })

    @action(detail=True, methods=['post'], url_path='discount')
    def discount(self, request, pk=None):
        order = self.get_object()
        disc_type = request.data.get('type', 'percent')
        disc_val = Decimal(str(request.data.get('value', 0) or 0))
        
        order.discount_type = disc_type
        order.discount_value = disc_val
        order.recalculate_totals()

        return Response({
            "status": "success",
            "message": "Chegirma qo'llandi",
            "order": self.get_serializer(order).data
        })

    @action(detail=True, methods=['post'], url_path='mark_paid')
    @transaction.atomic
    def mark_paid(self, request, pk=None):
        order = self.get_object()
        payment_type = request.data.get('payment_type') or request.data.get('payment_method') or 'cash'
        cash_amt = Decimal(str(request.data.get('cash_amount', 0) or 0))
        card_amt = Decimal(str(request.data.get('card_amount', 0) or 0))

        if payment_type == 'cash' and cash_amt == 0:
            cash_amt = order.total_amount
        elif payment_type == 'card' and card_amt == 0:
            card_amt = order.total_amount

        order.status = 'paid'
        order.payment_type = payment_type
        order.cash_amount = cash_amt
        order.card_amount = card_amt
        order.paid_at = timezone.now()
        order.closed_at = timezone.now()
        order.save()

        # Free table
        if order.table:
            order.table.status = 'free'
            order.table.is_busy = False
            order.table.save(update_fields=['status', 'is_busy', 'updated_at'])

        # Auto Deduct Inventory based on recipe BOM
        for item in order.items.all():
            product = item.product
            if not product:
                continue
            for ing in product.ingredients.all():
                raw_mat = ing.maxsulot
                if not raw_mat:
                    continue
                needed_qty = ing.amount * item.qty
                prev_stk = raw_mat.current_stock
                raw_mat.current_stock = max(0, prev_stk - needed_qty)
                raw_mat.save(update_fields=['current_stock', 'updated_at'])

                InventoryStockHistory.objects.create(
                    product=raw_mat,
                    movement_type='auto_deduct',
                    quantity=needed_qty,
                    previous_stock=prev_stk,
                    new_stock=raw_mat.current_stock,
                    reference_id=f"Buyurtma #{order.number or order.id}",
                    note=f"{product.name} x {item.qty} tayyorlanishi uchun avto chiqim"
                )

        # Record Finance Transaction
        cat, _ = FinanceCategory.objects.get_or_create(name="Sotuv tushumi", defaults={"category_type": "INCOME"})
        branch = order.branch or Branch.objects.first()
        acc_id = request.data.get('account_id')
        acc = None
        if acc_id:
            acc = FinanceAccount.objects.filter(id=acc_id).first()
        if not acc:
            acc = FinanceAccount.objects.filter(branch=branch, account_type='CASH' if payment_type == 'cash' else 'NON_CASH').first()
            if not acc:
                acc = FinanceAccount.objects.filter(branch=branch).first()

        if acc:
            acc.balance = (acc.balance or Decimal("0.00")) + order.total_amount
            acc.save(update_fields=['balance', 'updated_at'])

        FinanceTransaction.objects.create(
            branch=branch,
            account=acc,
            category=cat,
            transaction_type='INCOME',
            payment_type=payment_type,
            amount=order.total_amount,
            source='kassa',
            order=order,
            employee=order.assigned_waiter,
            description=f"Buyurtma #{order.number or order.id} to'lovi ({payment_type})",
            date=timezone.now().date()
        )

        logger.info(f"Buyurtma #{order.number or order.id} to'landi. Summa: {order.total_amount} UZS, To'lov turi: {payment_type}")

        return Response({
            "status": "success",
            "message": "To'lov muvaffaqiyatli amalga oshirildi",
            "order": self.get_serializer(order).data
        })

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all().select_related('order', 'product')
    serializer_class = OrderItemSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['order', 'product', 'status']

    def perform_create(self, serializer):
        item = serializer.save()
        item.order.recalculate_totals()

    def perform_update(self, serializer):
        item = serializer.save()
        item.order.recalculate_totals()

    def perform_destroy(self, instance):
        order = instance.order
        instance.delete()
        order.recalculate_totals()

class CheckoutPrintView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        order_id = request.data.get('order_id') or request.data.get('order')
        order = Order.objects.filter(id=order_id).first() if order_id else Order.objects.order_by('-id').first()
        
        check_set = ReceiptSettings.objects.first()
        cafe_name = check_set.cafe_name if check_set else "Bahor Cafe"
        address = check_set.address if check_set else "Toshkent sh."
        phone = check_set.phone if check_set else "+998 90 123 45 67"
        footer = check_set.footer_text if check_set else "Rahmat, yana keling!"

        items = []
        if order:
            for it in order.items.all():
                items.append({
                    "name": it.product_name_snapshot or it.product.name,
                    "qty": float(it.qty),
                    "price": float(it.unit_price),
                    "total": float(it.total_price)
                })

        return Response({
            "cafe_name": cafe_name,
            "address": address,
            "phone": phone,
            "order_number": order.number if order else 1001,
            "table": order.table.name if (order and order.table) else "—",
            "waiter": order.assigned_waiter.name if (order and order.assigned_waiter) else "Kassir",
            "date": timezone.now().strftime("%d.%m.%Y %H:%M"),
            "items": items,
            "subtotal": float(order.base_amount if order else 0),
            "discount": float(order.discount_amount if order else 0),
            "service_fee": float(order.service_amount if order else 0),
            "total": float(order.total_amount if order else 0),
            "footer": footer,
            "printed": True
        })

class ReceiptPrintView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        order_id = request.query_params.get('order_id')
        order = Order.objects.filter(id=order_id).first() if order_id else None
        
        check_set = ReceiptSettings.objects.first()
        return Response({
            "status": "success",
            "order_id": order_id,
            "cafe_name": check_set.cafe_name if check_set else "Bahor Cafe",
            "footer_text": check_set.footer_text if check_set else "Xaridingiz uchun rahmat!",
            "total_amount": float(order.total_amount if order else 0)
        })

class PaymentStartView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({
            "status": "success",
            "message": "To'lov jarayoni boshlandi",
            "payment_id": "PAY-" + str(int(timezone.now().timestamp()))
        })

class OrderReportsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        orders = Order.objects.filter(status='paid')
        total_rev = orders.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0')
        cnt = orders.count()

        serializer = OrderSerializer(orders[:50], many=True)
        return Response({
            "stats": {
                "jami_buyurtmalar": cnt,
                "jami_tushum": float(total_rev),
                "ortacha_chek": float(total_rev / cnt) if cnt > 0 else 0
            },
            "orders": serializer.data
        })
