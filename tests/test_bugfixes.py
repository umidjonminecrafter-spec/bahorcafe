from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from decimal import Decimal
import os

from apps.employee.models import Employee, Role
from apps.sozlamalar.models import Branch, OrderFlowSettings
from apps.table.models import Table, Product, ProductIngredient
from apps.order.models import Order, OrderItem
from apps.finance.models import FinanceAccount, FinanceCategory, FinanceTransaction
from apps.inventory.models import (
    Warehouse, Supplier, InventoryProduct, Purchase, PurchaseItem,
    Realization, RealizationItem, WriteOff, InventoryStockHistory
)

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

    def test_order_list_returns_cards_and_orders_table_and_results(self):
        """Test that /order/orders/ returns cards, orders_table, and results for frontend T8 component"""
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            qty=Decimal('1.0'),
            unit_price=Decimal('45000.0'),
            cost_price=Decimal('25000.0'),
            status='served'
        )
        res = self.client.get('/order/orders/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('cards', res.data)
        self.assertIn('orders_table', res.data)
        self.assertIn('results', res.data)

        # Check cards structure
        cards = res.data['cards']
        self.assertEqual(cards['jami_buyurtmalar'], 1)
        self.assertEqual(cards['tushum'], 45000.0)
        self.assertEqual(cards['bekor_qilingan'], 0)
        self.assertEqual(cards['ortacha_chek'], 45000.0)

        # Check orders_table structure
        self.assertEqual(len(res.data['orders_table']), 1)
        row = res.data['orders_table'][0]
        self.assertIn('buyurtma_raqami', row)
        self.assertIn('joylashuv', row)
        self.assertIn('ofitsiant', row)
        self.assertIn('mehmonlar_soni', row)
        self.assertIn('status', row)
        self.assertIn('sana_vaqt', row)
        self.assertIn('summa', row)
        self.assertEqual(row['status'], 'paid')
        self.assertEqual(row['summa'], 45000.0)

    def test_umumiy_hisobot_returns_dinamika_and_kassalar_statistikasi(self):
        """Test that /kitchen/umumiy-hisobot/ returns jami_tushum, dinamika, and kassalar_statistikasi for frontend Vbe component"""
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            qty=Decimal('1.0'),
            unit_price=Decimal('45000.0'),
            cost_price=Decimal('25000.0'),
            status='served'
        )
        res = self.client.get('/kitchen/umumiy-hisobot/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('jami_tushum', res.data)
        self.assertIn('jami_foyda', res.data)
        self.assertIn('dinamika', res.data)
        self.assertIn('kassalar_statistikasi', res.data)
        self.assertEqual(res.data['jami_tushum'], 45000.0)
        self.assertEqual(res.data['jami_foyda'], 20000.0)
        self.assertGreaterEqual(len(res.data['dinamika']), 1)
        self.assertGreaterEqual(len(res.data['kassalar_statistikasi']), 1)

    def test_sotuv_and_xodimlar_and_abc_reports(self):
        """Test that all kitchen report endpoints return 200 and expected fields"""
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            qty=Decimal('1.0'),
            unit_price=Decimal('45000.0'),
            cost_price=Decimal('25000.0'),
            status='served'
        )
        # Sotuv
        r_sotuv = self.client.get('/kitchen/sotuv-hisoboti/')
        self.assertEqual(r_sotuv.status_code, 200)
        self.assertGreaterEqual(len(r_sotuv.data), 1)
        self.assertIn('nomi', r_sotuv.data[0])
        self.assertIn('tushum', r_sotuv.data[0])

        # Xodimlar
        r_xodim = self.client.get('/kitchen/xodimlar-hisoboti/')
        self.assertEqual(r_xodim.status_code, 200)
        self.assertGreaterEqual(len(r_xodim.data), 1)
        self.assertIn('sotuvchi', r_xodim.data[0])
        self.assertIn('tushum', r_xodim.data[0])

        # ABC
        r_abc = self.client.get('/kitchen/abc-analysis/')
        self.assertEqual(r_abc.status_code, 200)
        self.assertGreaterEqual(len(r_abc.data), 1)
        self.assertIn('abc_class', r_abc.data[0])

    def test_inventory_purchases_list_and_stats(self):
        """Test that /inventory/purchases/ returns results and stats with expected fields"""
        wh = Warehouse.objects.create(name="Asosiy ombor", branch=self.branch)
        sup = Supplier.objects.create(name="Agro Meat MCHJ")
        prod = InventoryProduct.objects.create(name="Mol go'shti", warehouse=wh, purchase_price=Decimal('80000.0'), current_stock=Decimal('10.0'))
        
        # Create purchase
        res_create = self.client.post('/inventory/purchases/', {
            'warehouse': wh.id,
            'supplier': sup.id,
            'document_number': 'XARID-001',
            'items': [
                {'product': prod.id, 'quantity': 10, 'purchase_price': 80000, 'margin_percent': 25, 'selling_price': 100000}
            ]
        }, format='json')
        self.assertEqual(res_create.status_code, 201)

        # GET list
        res_list = self.client.get('/inventory/purchases/')
        self.assertEqual(res_list.status_code, 200)
        self.assertIn('stats', res_list.data)
        self.assertIn('results', res_list.data)
        self.assertEqual(res_list.data['stats']['umumiy_xaridlar'], 1)
        self.assertEqual(res_list.data['stats']['umumiy_summa'], 800000.0)
        self.assertEqual(res_list.data['stats']['mahsulotlar_soni'], 1)

        # Check item fields
        row = res_list.data['results'][0]
        self.assertEqual(row['supplier_name'], 'Agro Meat MCHJ')
        self.assertEqual(row['tamiNotchi'], 'Agro Meat MCHJ')
        self.assertEqual(row['ombor'], 'Asosiy ombor')
        self.assertEqual(row['hujjat_raqami'], 'XARID-001')

    def test_inventory_realizations_list_and_stats(self):
        """Test that /inventory/realizations/ returns results and stats with expected fields"""
        wh = Warehouse.objects.create(name="Asosiy ombor", branch=self.branch)
        prod = InventoryProduct.objects.create(name="Guruch", warehouse=wh, purchase_price=Decimal('25000.0'), selling_price=Decimal('35000.0'), current_stock=Decimal('50.0'))

        # Create realization
        res_create = self.client.post('/inventory/realizations/', {
            'warehouse': 'Asosiy ombor',
            'agent': 'Optom Xaridor',
            'document_number': 'REAL-001',
            'items': [
                {'product': prod.id, 'quantity': 10, 'purchase_price': 25000, 'selling_price': 35000}
            ]
        }, format='json')
        self.assertEqual(res_create.status_code, 201)

        # GET list
        res_list = self.client.get('/inventory/realizations/')
        self.assertEqual(res_list.status_code, 200)
        self.assertIn('stats', res_list.data)
        self.assertIn('results', res_list.data)
        self.assertEqual(res_list.data['stats']['jami_realizatsiyalar'], 1)
        self.assertEqual(res_list.data['stats']['umumiy_summa'], 350000.0)
        self.assertEqual(res_list.data['stats']['tovar_pozitsiyalari'], 1)

        row = res_list.data['results'][0]
        self.assertEqual(row['kontragent'], 'Optom Xaridor')
        self.assertEqual(row['ombor'], 'Asosiy ombor')
        self.assertEqual(row['doc_no'], 'REAL-001')

    def test_order_mark_paid_creates_realization(self):
        """Test that paying an order automatically logs a Realization in inventory"""
        wh = Warehouse.objects.create(name="Asosiy ombor", branch=self.branch)
        raw = InventoryProduct.objects.create(name="Go'sht", warehouse=wh, purchase_price=Decimal('80000.0'), current_stock=Decimal('20.0'))
        ProductIngredient.objects.create(product=self.product, maxsulot=raw, amount=Decimal('0.2'), unit='kg')

        order = Order.objects.create(
            branch=self.branch,
            table=self.table,
            assigned_waiter=self.employee,
            status='open',
            number=9999
        )
        OrderItem.objects.create(order=order, product=self.product, qty=Decimal('2.0'), unit_price=Decimal('45000.0'), cost_price=Decimal('25000.0'))
        order.recalculate_totals()

        res_pay = self.client.post(f'/order/orders/{order.id}/mark_paid/', {'payment_type': 'cash'}, format='json')
        self.assertEqual(res_pay.status_code, 200)

        # Check that Realization exists
        real = Realization.objects.filter(document_number=f"BUYURTMA-{order.number}").first()
        self.assertIsNotNone(real)
        self.assertEqual(real.total_amount, Decimal('99000.00')) # 90000 + 10% service

