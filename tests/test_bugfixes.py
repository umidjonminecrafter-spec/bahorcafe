from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from decimal import Decimal
import os

from apps.employee.models import Employee, Role
from apps.sozlamalar.models import Branch, OrderFlowSettings
from apps.table.models import Table, Product
from apps.order.models import Order, OrderItem
from apps.finance.models import FinanceAccount, FinanceCategory, FinanceTransaction

class BugfixesTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = Branch.objects.create(name="Bahor Cafe", city="Farg'ona")
        self.role = Role.objects.create(name="ADMIN", salary_type="fixed", salary_amount=5000000)
        self.user = User.objects.create_user(username="998901112233", password="testpassword123")
        self.employee = Employee.objects.create(
            user=self.user,
            name="Test User",
            phone="998901112233",
            role=self.role,
            branch=self.branch
        )
        self.table = Table.objects.create(branch=self.branch, name="Stol 1")
        self.product = Product.objects.create(name="Osh", price=Decimal('45000.0'), cost_price=Decimal('25000.0'))
        
        # Create paid order for report testing
        self.order = Order.objects.create(
            branch=self.branch,
            table=self.table,
            assigned_waiter=self.employee,
            status='paid',
            total_amount=Decimal('45000.0')
        )

    def test_order_reports_sum_import_fixed(self):
        """Test that /order/reports/ does not crash with NameError for Sum"""
        res = self.client.get('/order/reports/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('stats', res.data)
        self.assertEqual(res.data['stats']['jami_buyurtmalar'], 1)
        self.assertEqual(res.data['stats']['jami_tushum'], 45000.0)

    def test_order_flow_routes_in_sozlamalar(self):
        """Test that /sozlamalar/order-flow/ and /sozlamalar/order-flow-settings/ exist and return 200"""
        res1 = self.client.get('/sozlamalar/order-flow/')
        self.assertEqual(res1.status_code, 200)
        self.assertIn('auto_kitchen', res1.data)

        res2 = self.client.get('/sozlamalar/order-flow-settings/')
        self.assertEqual(res2.status_code, 200)

    def test_me_view_security(self):
        """Test that unauthenticated requests to /employee/auth/me/ return 401"""
        res_anon = self.client.get('/employee/auth/me/')
        self.assertEqual(res_anon.status_code, 401)

        # Authenticated
        self.client.force_authenticate(user=self.user)
        res_auth = self.client.get('/employee/auth/me/')
        self.assertEqual(res_auth.status_code, 200)
        self.assertEqual(res_auth.data['name'], 'Test User')

    def test_finance_balance_sync_on_update_and_delete(self):
        """Test that updating and deleting finance transactions correctly updates account balance"""
        acc = FinanceAccount.objects.create(
            branch=self.branch,
            name="Test Kassa",
            account_type='CASH',
            balance=Decimal('100000.0')
        )
        cat = FinanceCategory.objects.create(name="Xarajat", category_type='EXPENSE')

        # 1. Create expense transaction (-30000)
        res = self.client.post('/finance/transactions/', {
            'branch': self.branch.id,
            'account': acc.id,
            'category': cat.id,
            'transaction_type': 'EXPENSE',
            'amount': '30000.00',
            'payment_type': 'cash',
            'source': 'manual',
            'description': 'Mahsulot xaridi'
        }, format='json')
        self.assertEqual(res.status_code, 201)
        acc.refresh_from_db()
        self.assertEqual(acc.balance, Decimal('70000.00'))

        tr_id = res.data['id']

        # 2. Update expense transaction amount from 30000 to 20000 (balance should be 80000)
        res_patch = self.client.patch(f'/finance/transactions/{tr_id}/', {
            'amount': '20000.00'
        }, format='json')
        self.assertEqual(res_patch.status_code, 200)
        acc.refresh_from_db()
        self.assertEqual(acc.balance, Decimal('80000.00'))

        # 3. Delete expense transaction (balance should revert back to 100000)
        res_del = self.client.delete(f'/finance/transactions/{tr_id}/')
        self.assertEqual(res_del.status_code, 204)
        acc.refresh_from_db()
        self.assertEqual(acc.balance, Decimal('100000.00'))

    def test_order_number_auto_increment(self):
        """Test Order number increments properly"""
        o1 = Order.objects.create(branch=self.branch)
        o2 = Order.objects.create(branch=self.branch)
        self.assertGreater(o2.number, o1.number)

    def test_logging_directory_and_file_creation(self):
        """Test that logs directory and log file exists"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        self.assertTrue(os.path.exists(log_dir))
