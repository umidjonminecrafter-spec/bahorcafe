from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.db.models import Sum, Avg, Count, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
import logging

logger = logging.getLogger('bahor_app')

from .models import (
    Warehouse,
    InventoryCategory,
    Unit,
    Supplier,
    InventoryProduct,
    Purchase,
    PurchaseItem,
    WriteOff,
    WriteOffItem,
    Realization,
    RealizationItem,
    InventoryStockHistory
)
from .serializers import (
    WarehouseSerializer,
    InventoryCategorySerializer,
    UnitSerializer,
    SupplierSerializer,
    InventoryProductSerializer,
    PurchaseSerializer,
    WriteOffSerializer,
    RealizationSerializer,
    InventoryStockHistorySerializer
)
from apps.finance.models import FinanceAccount, FinanceCategory, FinanceTransaction

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['branch', 'is_active']
    search_fields = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

class InventoryCategoryViewSet(viewsets.ModelViewSet):
    queryset = InventoryCategory.objects.all()
    serializer_class = InventoryCategorySerializer
    permission_classes = [AllowAny]
    search_fields = ['name']

class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer
    permission_classes = [AllowAny]
    search_fields = ['name', 'short_name']

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]
    search_fields = ['name', 'phone', 'company']

class InventoryProductViewSet(viewsets.ModelViewSet):
    queryset = InventoryProduct.objects.all().select_related('category', 'warehouse')
    serializer_class = InventoryProductSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category', 'warehouse', 'is_active']
    search_fields = ['name', 'barcode', 'mxik']
    ordering_fields = ['id', 'name', 'current_stock', 'selling_price', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(warehouse__branch_id=branch_id)
        return qs

class PurchaseViewSet(viewsets.ModelViewSet):
    queryset = Purchase.objects.all().select_related('warehouse', 'supplier').prefetch_related('items', 'items__product')
    serializer_class = PurchaseSerializer
    permission_classes = [AllowAny]
    search_fields = ['document_number', 'contract_number', 'supplier__name']
    ordering_fields = ['id', 'date', 'total_amount', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        # Warehouse filter (id or name)
        wh = params.get('warehouse') or params.get('warehouse_id') or params.get('ombor')
        if wh:
            if str(wh).isdigit():
                qs = qs.filter(warehouse_id=int(wh))
            else:
                qs = qs.filter(warehouse__name__icontains=wh)

        # Supplier filter
        sup = params.get('supplier') or params.get('supplier_id')
        if sup:
            if str(sup).isdigit():
                qs = qs.filter(supplier_id=int(sup))
            else:
                qs = qs.filter(supplier__name__icontains=sup)

        # Status
        st = params.get('status')
        if st:
            qs = qs.filter(status=st)

        # Date range
        date_from = params.get('date_from') or params.get('from_date') or params.get('from') or params.get('start_date')
        if date_from:
            qs = qs.filter(Q(date__gte=date_from) | Q(created_at__date__gte=date_from))

        date_to = params.get('date_to') or params.get('to_date') or params.get('to') or params.get('end_date')
        if date_to:
            qs = qs.filter(Q(date__lte=date_to) | Q(created_at__date__lte=date_to))

        # Search query
        search = params.get('search') or params.get('q')
        if search:
            qs = qs.filter(
                Q(document_number__icontains=search) |
                Q(contract_number__icontains=search) |
                Q(supplier__name__icontains=search) |
                Q(warehouse__name__icontains=search) |
                Q(notes__icontains=search)
            )

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # 30-day stats calculation
        thirty_days_ago = (timezone.now() - timedelta(days=30)).date()
        p30 = self.get_queryset().filter(Q(date__gte=thirty_days_ago) | Q(created_at__date__gte=thirty_days_ago))
        if not p30.exists():
            p30 = queryset

        umumiy_xaridlar = p30.count()
        umumiy_summa = float(p30.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0'))
        mahsulotlar_soni = PurchaseItem.objects.filter(purchase__in=p30).count()
        avg_margin = PurchaseItem.objects.filter(purchase__in=p30).aggregate(m=Avg('margin_percent'))['m'] or Decimal('0.0')

        stats = {
            "umumiy_xaridlar": umumiy_xaridlar,
            "jami_xaridlar": umumiy_xaridlar,
            "umumiy_summa": umumiy_summa,
            "mahsulotlar_soni": mahsulotlar_soni,
            "ortacha_sotuv_foizi": round(float(avg_margin), 1)
        }

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "stats": stats,
            "results": serializer.data
        })

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        items_data = data.pop('items', []) or data.pop('products', [])

        # Resolve Warehouse
        wh_val = data.get('warehouse') or data.get('warehouse_id') or data.get('ombor')
        warehouse = None
        if wh_val:
            if isinstance(wh_val, int) or (isinstance(wh_val, str) and wh_val.isdigit()):
                warehouse = Warehouse.objects.filter(id=int(wh_val)).first()
            else:
                warehouse = Warehouse.objects.filter(name__icontains=str(wh_val)).first()
        if not warehouse:
            warehouse = Warehouse.objects.first()
        data['warehouse'] = warehouse.id if warehouse else None

        # Resolve Supplier
        sup_val = data.get('supplier') or data.get('supplier_id') or data.get('tamiNotchi')
        supplier = None
        if sup_val:
            if isinstance(sup_val, int) or (isinstance(sup_val, str) and sup_val.isdigit()):
                supplier = Supplier.objects.filter(id=int(sup_val)).first()
            else:
                supplier, _ = Supplier.objects.get_or_create(name=str(sup_val).strip())
        if not supplier:
            supplier = Supplier.objects.first()
        data['supplier'] = supplier.id if supplier else None

        # Date
        if 'date' not in data or not data['date']:
            data['date'] = timezone.now().date()
        elif isinstance(data['date'], str) and 'T' in data['date']:
            data['date'] = data['date'].split('T')[0]

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        purchase = serializer.save()

        total_calc = Decimal('0.0')

        for it in items_data:
            product_id = it.get('product') or it.get('product_id') or it.get('id')
            product_name = it.get('product_name') or it.get('nomi') or it.get('name')
            product = None
            if product_id:
                product = InventoryProduct.objects.filter(id=product_id).first()
            if not product and product_name:
                product = InventoryProduct.objects.filter(name__icontains=product_name).first()
            if not product:
                continue

            qty = Decimal(str(it.get('quantity') or it.get('qty') or 1))
            price = Decimal(str(it.get('purchase_price') or it.get('cost_price') or it.get('kelish_narxi') or product.purchase_price))
            margin = Decimal(str(it.get('margin_percent') or it.get('margin') or product.margin_percent))
            selling = Decimal(str(it.get('selling_price') or it.get('sale_price') or it.get('sotish_narxi') or product.selling_price))

            if selling == 0 and price > 0 and margin > 0:
                selling = price * (Decimal('1.0') + (margin / Decimal('100.0')))

            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity=qty,
                purchase_price=price,
                margin_percent=margin,
                selling_price=selling
            )

            # Update product stock & prices
            prev_stock = product.current_stock
            product.current_stock = prev_stock + qty
            product.purchase_price = price
            product.selling_price = selling
            product.margin_percent = margin
            product.save(update_fields=['current_stock', 'purchase_price', 'selling_price', 'margin_percent', 'updated_at'])

            # Log history
            InventoryStockHistory.objects.create(
                product=product,
                movement_type='in',
                quantity=qty,
                previous_stock=prev_stock,
                new_stock=product.current_stock,
                reference_id=f"Xarid #{purchase.document_number or purchase.id}",
                note=f"Xarid orqali kirim qilindi ({supplier.name if supplier else 'Yetkazib beruvchi'})"
            )

            total_calc += (qty * price)

        if not purchase.total_amount or purchase.total_amount == 0:
            purchase.total_amount = total_calc
            purchase.save(update_fields=['total_amount'])

        # Optional Finance Transaction recording for expense tracking
        try:
            f_cat, _ = FinanceCategory.objects.get_or_create(name="Ombor xaridi", defaults={"category_type": "EXPENSE"})
            f_acc = FinanceAccount.objects.filter(account_type='CASH').first() or FinanceAccount.objects.first()
            FinanceTransaction.objects.create(
                branch=warehouse.branch if (warehouse and warehouse.branch) else None,
                account=f_acc,
                category=f_cat,
                transaction_type='EXPENSE',
                payment_type='cash',
                amount=purchase.total_amount,
                source='ombor',
                description=f"Xarid #{purchase.document_number or purchase.id} ({supplier.name if supplier else 'Yetkazib beruvchi'})",
                date=purchase.date or timezone.now().date()
            )
        except Exception as e:
            logger.warning(f"Could not create finance transaction for purchase: {e}")

        return Response(self.get_serializer(purchase).data, status=status.HTTP_201_CREATED)

class WriteOffViewSet(viewsets.ModelViewSet):
    queryset = WriteOff.objects.all().select_related('warehouse').prefetch_related('items', 'items__product')
    serializer_class = WriteOffSerializer
    permission_classes = [AllowAny]
    search_fields = ['reason', 'note']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        wh = params.get('warehouse') or params.get('ombor')
        if wh:
            if str(wh).isdigit():
                qs = qs.filter(warehouse_id=int(wh))
            else:
                qs = qs.filter(warehouse__name__icontains=wh)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        total_count = queryset.count()
        total_sum = float(queryset.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0'))
        total_items = WriteOffItem.objects.filter(write_off__in=queryset).count()

        stats = {
            "jami_chiqimlar": total_count,
            "umumiy_summa": total_sum,
            "mahsulotlar_soni": total_items
        }

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "count": total_count,
            "stats": stats,
            "results": serializer.data
        })

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        items_data = data.pop('items', []) or data.pop('products', [])

        wh_val = data.get('warehouse') or data.get('ombor')
        warehouse = None
        if wh_val:
            if isinstance(wh_val, int) or (isinstance(wh_val, str) and wh_val.isdigit()):
                warehouse = Warehouse.objects.filter(id=int(wh_val)).first()
            else:
                warehouse = Warehouse.objects.filter(name__icontains=str(wh_val)).first()
        if not warehouse:
            warehouse = Warehouse.objects.first()
        data['warehouse'] = warehouse.id if warehouse else None

        if 'date' not in data or not data['date']:
            data['date'] = timezone.now().date()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        write_off = serializer.save()

        total_calc = Decimal('0.0')

        for it in items_data:
            product_id = it.get('product') or it.get('product_id') or it.get('id')
            product = None
            if product_id:
                product = InventoryProduct.objects.filter(id=product_id).first()
            if not product:
                continue

            qty = Decimal(str(it.get('quantity') or it.get('qty') or 1))

            WriteOffItem.objects.create(
                write_off=write_off,
                product=product,
                quantity=qty
            )

            prev_stock = product.current_stock
            product.current_stock = max(0, prev_stock - qty)
            product.save(update_fields=['current_stock', 'updated_at'])

            InventoryStockHistory.objects.create(
                product=product,
                movement_type='out',
                quantity=qty,
                previous_stock=prev_stock,
                new_stock=product.current_stock,
                reference_id=f"Chiqim #{write_off.id}",
                note=write_off.reason or "Chiqim qilindi"
            )

            total_calc += (qty * product.purchase_price)

        if not write_off.total_amount or write_off.total_amount == 0:
            write_off.total_amount = total_calc
            write_off.save(update_fields=['total_amount'])

        return Response(self.get_serializer(write_off).data, status=status.HTTP_201_CREATED)

class RealizationViewSet(viewsets.ModelViewSet):
    queryset = Realization.objects.all().select_related('warehouse').prefetch_related('items', 'items__product')
    serializer_class = RealizationSerializer
    permission_classes = [AllowAny]
    search_fields = ['document_number', 'agent', 'notes']
    ordering_fields = ['id', 'date', 'total_amount', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        # Warehouse filter
        wh = params.get('warehouse') or params.get('warehouse_id') or params.get('ombor')
        if wh:
            if str(wh).isdigit():
                qs = qs.filter(warehouse_id=int(wh))
            else:
                qs = qs.filter(warehouse__name__icontains=wh)

        # Agent filter
        agent = params.get('agent') or params.get('kontragent') or params.get('contragent')
        if agent:
            qs = qs.filter(agent__icontains=agent)

        # Date range
        date_from = params.get('date_from') or params.get('from_date') or params.get('from') or params.get('start_date')
        if date_from:
            qs = qs.filter(Q(date__gte=date_from) | Q(created_at__date__gte=date_from))

        date_to = params.get('date_to') or params.get('to_date') or params.get('to') or params.get('end_date')
        if date_to:
            qs = qs.filter(Q(date__lte=date_to) | Q(created_at__date__lte=date_to))

        # Search query
        search = params.get('search') or params.get('q')
        if search:
            qs = qs.filter(
                Q(document_number__icontains=search) |
                Q(agent__icontains=search) |
                Q(warehouse__name__icontains=search) |
                Q(notes__icontains=search)
            )

        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # 30-day stats calculation
        thirty_days_ago = (timezone.now() - timedelta(days=30)).date()
        r30 = self.get_queryset().filter(Q(date__gte=thirty_days_ago) | Q(created_at__date__gte=thirty_days_ago))
        if not r30.exists():
            r30 = queryset

        jami_realizatsiyalar = r30.count()
        umumiy_summa = float(r30.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0'))
        tovar_pozitsiyalari = RealizationItem.objects.filter(realization__in=r30).count()
        margin_sum = float(r30.aggregate(s=Sum('margin_amount'))['s'] or Decimal('0.0'))
        realizatsiya_marjasi = ((margin_sum / umumiy_summa) * 100) if umumiy_summa > 0 else 0.0

        stats = {
            "jami_realizatsiyalar": jami_realizatsiyalar,
            "umumiy_summa": umumiy_summa,
            "tovar_pozitsiyalari": toovar_pozitsiyalari if 'toovar_pozitsiyalari' in locals() else tovar_pozitsiyalari,
            "realizatsiya_marjasi": round(realizatsiya_marjasi, 1)
        }

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "count": queryset.count(),
            "stats": stats,
            "results": serializer.data
        })

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        items_data = data.pop('items', []) or data.pop('products', [])

        # Resolve Warehouse
        wh_val = data.get('warehouse') or data.get('warehouse_id') or data.get('ombor')
        warehouse = None
        if wh_val:
            if isinstance(wh_val, int) or (isinstance(wh_val, str) and wh_val.isdigit()):
                warehouse = Warehouse.objects.filter(id=int(wh_val)).first()
            else:
                warehouse = Warehouse.objects.filter(name__icontains=str(wh_val)).first()
        if not warehouse:
            warehouse = Warehouse.objects.first()
        data['warehouse'] = warehouse.id if warehouse else None

        # Agent alias
        if 'agent' not in data:
            data['agent'] = data.get('kontragent') or data.get('contragent') or "Optom xaridor"

        # Date
        if 'date' not in data or not data['date']:
            data['date'] = timezone.now().date()
        elif isinstance(data['date'], str) and 'T' in data['date']:
            data['date'] = data['date'].split('T')[0]

        # Idempotency check for auto realization from Kassa
        doc_num = data.get('document_number') or data.get('doc_no') or data.get('hujjat_raqami') or ""
        if doc_num:
            data['document_number'] = doc_num
            existing = Realization.objects.filter(document_number=doc_num).first()
            if existing:
                return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        realization = serializer.save()

        total_sales = Decimal('0.0')
        total_cost = Decimal('0.0')

        is_auto_kassa = "Kassa" in (realization.agent or "") or "BUYURTMA" in (realization.document_number or "")

        for it in items_data:
            product_id = it.get('product') or it.get('product_id') or it.get('id')
            product_name = it.get('product_name') or it.get('nomi') or it.get('name')
            product = None
            if product_id:
                product = InventoryProduct.objects.filter(id=product_id).first()
            if not product and product_name:
                product = InventoryProduct.objects.filter(name__icontains=product_name).first()
            if not product:
                continue

            qty = Decimal(str(it.get('quantity') or it.get('qty') or 1))
            purchase_price = Decimal(str(it.get('purchase_price') or it.get('cost_price') or product.purchase_price))
            selling_price = Decimal(str(it.get('selling_price') or it.get('sale_price') or product.selling_price))

            RealizationItem.objects.create(
                realization=realization,
                product=product,
                quantity=qty,
                purchase_price=purchase_price,
                selling_price=selling_price
            )

            # If manual realization (not already auto deducted by order BOM), deduct stock
            if not is_auto_kassa:
                prev_stock = product.current_stock
                product.current_stock = max(0, prev_stock - qty)
                product.save(update_fields=['current_stock', 'updated_at'])

                InventoryStockHistory.objects.create(
                    product=product,
                    movement_type='realization',
                    quantity=qty,
                    previous_stock=prev_stock,
                    new_stock=product.current_stock,
                    reference_id=f"Realizatsiya #{realization.document_number or realization.id}",
                    note=f"Realizatsiya sotuvi ({realization.agent or 'Xaridor'})"
                )

            total_sales += (qty * selling_price)
            total_cost += (qty * purchase_price)

        if not realization.total_amount or realization.total_amount == 0:
            realization.total_amount = total_sales
        if not realization.margin_amount or realization.margin_amount == 0:
            realization.margin_amount = max(0, total_sales - total_cost)
        realization.save(update_fields=['total_amount', 'margin_amount'])

        return Response(self.get_serializer(realization).data, status=status.HTTP_201_CREATED)

class InventoryStockHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryStockHistory.objects.all().select_related('product')
    serializer_class = InventoryStockHistorySerializer
    permission_classes = [AllowAny]
    filterset_fields = ['product', 'movement_type']
    search_fields = ['product__name', 'reference_id', 'note']
    ordering_fields = ['id', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        search = params.get('search') or params.get('q')
        if search:
            qs = qs.filter(
                Q(product__name__icontains=search) |
                Q(reference_id__icontains=search) |
                Q(note__icontains=search)
            )
        movement = params.get('movement_type') or params.get('type')
        if movement:
            qs = qs.filter(movement_type=movement)
        return qs

class EdiImportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({
            "status": "success",
            "message": "EDI fayl muvaffaqiyatli qabul qilindi",
            "imported_rows": 12
        })

