from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from .models import FinanceAccount, FinanceCategory, FinanceTransaction
from .serializers import FinanceAccountSerializer, FinanceCategorySerializer, FinanceTransactionSerializer

class FinanceAccountViewSet(viewsets.ModelViewSet):
    queryset = FinanceAccount.objects.all()
    serializer_class = FinanceAccountSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['branch', 'account_type', 'is_active']
    search_fields = ['name']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

class FinanceCategoryViewSet(viewsets.ModelViewSet):
    queryset = FinanceCategory.objects.all()
    serializer_class = FinanceCategorySerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category_type', 'is_active']
    search_fields = ['name']

from django.db import transaction
import logging

logger = logging.getLogger('bahor_app')

class FinanceTransactionViewSet(viewsets.ModelViewSet):
    queryset = FinanceTransaction.objects.all().select_related('account', 'category', 'branch', 'employee')
    serializer_class = FinanceTransactionSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['branch', 'account', 'category', 'transaction_type', 'source', 'payment_type']
    search_fields = ['description', 'employee__name']
    ordering_fields = ['id', 'date', 'amount', 'created_at']

    def get_queryset(self):
        qs = super().get_queryset()
        branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        tr = serializer.save()
        if tr.account:
            if tr.transaction_type == 'INCOME':
                tr.account.balance += tr.amount
            else:
                tr.account.balance = max(Decimal('0.0'), tr.account.balance - tr.amount)
            tr.account.save(update_fields=['balance', 'updated_at'])
            logger.info(f"Moliya tranzaksiyasi yaratildi: ID={tr.id}, Tur={tr.transaction_type}, Summa={tr.amount}, Hisob={tr.account.name}")

    @transaction.atomic
    def perform_update(self, serializer):
        old_tr = self.get_object()
        old_acc = old_tr.account
        old_amt = old_tr.amount
        old_type = old_tr.transaction_type

        # Revert old impact on previous account
        if old_acc:
            if old_type == 'INCOME':
                old_acc.balance = max(Decimal('0.0'), old_acc.balance - old_amt)
            else:
                old_acc.balance += old_amt
            old_acc.save(update_fields=['balance', 'updated_at'])

        new_tr = serializer.save()
        # Apply new impact
        if new_tr.account:
            # Refresh from DB if same account
            if old_acc and old_acc.id == new_tr.account.id:
                new_tr.account.refresh_from_db()
            if new_tr.transaction_type == 'INCOME':
                new_tr.account.balance += new_tr.amount
            else:
                new_tr.account.balance = max(Decimal('0.0'), new_tr.account.balance - new_tr.amount)
            new_tr.account.save(update_fields=['balance', 'updated_at'])
            logger.info(f"Moliya tranzaksiyasi yangilandi: ID={new_tr.id}, Yangi Summa={new_tr.amount}")

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.account:
            if instance.transaction_type == 'INCOME':
                instance.account.balance = max(Decimal('0.0'), instance.account.balance - instance.amount)
            else:
                instance.account.balance += instance.amount
            instance.account.save(update_fields=['balance', 'updated_at'])
            logger.info(f"Moliya tranzaksiyasi o'chirildi: ID={instance.id}, Balans tiklandi: {instance.account.name}")
        instance.delete()

class FinanceMonitoringView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        branch_id = request.query_params.get('branch_id') or request.query_params.get('branch')
        
        tr_qs = FinanceTransaction.objects.all()
        acc_qs = FinanceAccount.objects.all()
        if branch_id:
            tr_qs = tr_qs.filter(branch_id=branch_id)
            acc_qs = acc_qs.filter(branch_id=branch_id)

        jami_daromad = tr_qs.filter(transaction_type='INCOME').aggregate(s=Sum('amount'))['s'] or Decimal('0.0')
        jami_xarajat = tr_qs.filter(transaction_type='EXPENSE').aggregate(s=Sum('amount'))['s'] or Decimal('0.0')
        sof_foyda = jami_daromad - jami_xarajat

        naqd_qoldiq = acc_qs.filter(account_type='CASH').aggregate(s=Sum('balance'))['s'] or Decimal('0.0')
        karta_qoldiq = acc_qs.filter(account_type='NON_CASH').aggregate(s=Sum('balance'))['s'] or Decimal('0.0')
        bank_qoldiq = acc_qs.filter(account_type='BANK').aggregate(s=Sum('balance'))['s'] or Decimal('0.0')

        # Recent transactions
        recent = tr_qs.order_by('-id')[:10]
        recent_data = FinanceTransactionSerializer(recent, many=True).data

        return Response({
            "jami_daromad": float(jami_daromad),
            "jami_xarajat": float(jami_xarajat),
            "sof_foyda": float(sof_foyda),
            "hisoblar": {
                "naqd": float(naqd_qoldiq),
                "karta": float(karta_qoldiq),
                "bank": float(bank_qoldiq),
                "jami": float(naqd_qoldiq + karta_qoldiq + bank_qoldiq)
            },
            "songgi_tranzaksiyalar": recent_data
        })
