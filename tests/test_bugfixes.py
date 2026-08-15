from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import os

from apps.employee.models import Employee, Role
from apps.sozlamalar.models import Branch, OrderFlowSettings, TelegramBotSettings
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
        self.assertEqual(real.total_amount, Decimal('90000.00')) # 90000 (0% service fee)

    def test_telegram_settings_api(self):
        """Test GET and PUT for /sozlamalar/telegram-settings/"""
        # GET
        res_get = self.client.get('/sozlamalar/telegram-settings/')
        self.assertEqual(res_get.status_code, 200)
        self.assertIn('bot_token', res_get.data)
        self.assertIn('chat_id', res_get.data)

        # PUT
        res_put = self.client.put('/sozlamalar/telegram-settings/', {
            'bot_token': '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11',
            'chat_id': '-1001234567890',
            'is_active': True,
            'notify_order_paid': True,
            'notify_order_cancelled': True,
            'notify_daily_report': True
        }, format='json')
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.data['bot_token'], '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11')
        self.assertEqual(res_put.data['chat_id'], '-1001234567890')

    def test_order_cancel_action(self):
        """Test cancelling order via /order/orders/{id}/cancel/"""
        order = Order.objects.create(
            branch=self.branch,
            table=self.table,
            assigned_waiter=self.employee,
            status='open',
            number=8888
        )
        self.table.status = 'busy'
        self.table.save()

        res_cancel = self.client.post(f'/order/orders/{order.id}/cancel/', {
            'reason': 'Mijoz shoshilayotgan ekan'
        }, format='json')
        self.assertEqual(res_cancel.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, 'free')

    def test_telegram_daily_report_generation(self):
        """Test daily summary generation logic"""
        from apps.core.telegram import send_daily_summary_report
        # Create a paid order
        order = Order.objects.create(
            branch=self.branch,
            table=self.table,
            assigned_waiter=self.employee,
            status='paid',
            payment_type='cash',
            total_amount=Decimal('150000.0'),
            number=7777
        )
        OrderItem.objects.create(order=order, product=self.product, qty=Decimal('3.0'), unit_price=Decimal('50000.0'), total_price=Decimal('150000.0'))

        ok, report = send_daily_summary_report(branch=self.branch, target_date=timezone.localdate(), async_send=False)
        self.assertIn('total_revenue', report)
        self.assertGreaterEqual(report['total_revenue'], 150000.0)
        self.assertGreaterEqual(report['paid_count'], 1)

    def test_telegram_phone_auth_flow(self):
        """Test user sends /start then sends phone contact to authorize"""
        from apps.core.telegram import process_telegram_update
        
        # 1. User sends /start
        up1 = {
            "update_id": 1001,
            "message": {
                "message_id": 1,
                "from": {"id": 99887766, "first_name": "Umidjon"},
                "chat": {"id": 99887766, "type": "private"},
                "text": "/start"
            }
        }
        res1 = process_telegram_update(up1)
        self.assertEqual(res1.get('status'), 'start_processed')

        # 2. User shares contact
        up2 = {
            "update_id": 1002,
            "message": {
                "message_id": 2,
                "from": {"id": 99887766, "first_name": "Umidjon"},
                "chat": {"id": 99887766, "type": "private"},
                "contact": {
                    "phone_number": "+998901112233",
                    "first_name": "Umidjon"
                }
            }
        }
        res2 = process_telegram_update(up2)
        self.assertEqual(res2.get('status'), 'authorized')

        # Check DB linked
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.telegram_chat_id, "99887766")
        bot_set = TelegramBotSettings.objects.first()
        self.assertIn("99887766", bot_set.chat_id)

    def test_telegram_non_admin_rejected(self):
        """Test non-admin employee (e.g. Waiter) is rejected when trying to link bot"""
        from apps.core.telegram import process_telegram_update
        waiter_role = Role.objects.create(name="WAITER")
        waiter = Employee.objects.create(
            name="Oddiy Ofitsiant",
            phone="998935554433",
            role=waiter_role,
            branch=self.branch
        )
        up = {
            "update_id": 1003,
            "message": {
                "message_id": 3,
                "from": {"id": 11223344, "first_name": "Ofitsiant"},
                "chat": {"id": 11223344, "type": "private"},
                "contact": {
                    "phone_number": "+998935554433",
                    "first_name": "Ofitsiant"
                }
            }
        }
        res = process_telegram_update(up)
        self.assertEqual(res.get('status'), 'forbidden')
        waiter.refresh_from_db()
        self.assertEqual(waiter.telegram_chat_id, "")

    def test_telegram_stranger_rejected(self):
        """Test random stranger phone is rejected"""
        from apps.core.telegram import process_telegram_update
        up = {
            "update_id": 1004,
            "message": {
                "message_id": 4,
                "from": {"id": 55667788, "first_name": "Stranger"},
                "chat": {"id": 55667788, "type": "private"},
                "contact": {
                    "phone_number": "+998990009988",
                    "first_name": "Stranger"
                }
            }
        }
        res = process_telegram_update(up)
        self.assertEqual(res.get('status'), 'forbidden')

    def test_telegram_webhook_endpoint(self):
        """Test POST /sozlamalar/telegram-webhook/"""
        res = self.client.post('/sozlamalar/telegram-webhook/', {
            "update_id": 2001,
            "message": {
                "message_id": 5,
                "from": {"id": 12345, "first_name": "Test"},
                "chat": {"id": 12345, "type": "private"},
                "text": "/start"
            }
        }, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data.get('status'), 'start_processed')

    def test_salary_simulation_models(self):
        """Test calculation formulas for Fiksa, Smena, Foizli, Fiksa+Foiz, Soatlik"""
        # 1. Fiksa (4,000,000)
        res1 = self.client.post('/employee/salary/simulate/', {
            "type": "fiksa",
            "params": {"summa": "4 000 000"},
            "metrics": {}
        }, format='json')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.data['calculated_amount'], 4000000)

        # 2. Smena (200,000 x 22 smena = 4,400,000)
        res2 = self.client.post('/employee/salary/simulate/', {
            "type": "smena",
            "params": {"smena_narxi": "200 000"},
            "metrics": {"shiftsCount": "22"}
        }, format='json')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.data['calculated_amount'], 4400000)

        # 3. Foizli (50,000,000 x 5% = 2,500,000)
        res3 = self.client.post('/employee/salary/simulate/', {
            "type": "foizli",
            "params": {"foiz": "5"},
            "metrics": {"ordersTotal": "50 000 000"}
        }, format='json')
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.data['calculated_amount'], 2500000)

        # 4. Fiksa + Foiz (2,000,000 + 40,000,000 x 3% = 3,200,000)
        res4 = self.client.post('/employee/salary/simulate/', {
            "type": "fiksa_foiz",
            "params": {"baza_summa": "2 000 000", "qoshimcha_foiz": "3"},
            "metrics": {"ordersTotal": "40 000 000"}
        }, format='json')
        self.assertEqual(res4.status_code, 200)
        self.assertEqual(res4.data['calculated_amount'], 3200000)

        # 5. Soatlik (20,000 x 160 soat = 3,200,000)
        res5 = self.client.post('/employee/salary/simulate/', {
            "type": "soatlik",
            "params": {"stavka": "20 000"},
            "metrics": {"hoursWorked": "160"}
        }, format='json')
        self.assertEqual(res5.status_code, 200)
        self.assertEqual(res5.data['calculated_amount'], 3200000)





