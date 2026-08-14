import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.employee.models import Employee, Role, RoleModulePermission
from apps.sozlamalar.models import Branch, RestaurantSettings
from apps.table.models import Table, ProductCategory, Product, ProductIngredient
from apps.kitchen.models import Department, SemiProduct
from apps.inventory.models import Warehouse, InventoryCategory, Unit, InventoryProduct
from apps.finance.models import FinanceAccount, FinanceCategory, FinanceTransaction
from apps.order.models import Order, OrderItem

class FullE2EIntegrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.branch = Branch.objects.create(name="Bahor Cafe", city="Toshkent", is_active=True)
        self.role = Role.objects.create(name="ADMIN", salary_type="fixed", salary_amount=Decimal("8000000.00"))
        
        # Modules
        for mod in ["dashboard", "kassa", "menu", "ombor", "finance", "staff", "settings", "analytics"]:
            RoleModulePermission.objects.create(role=self.role, module=mod, can_view=True, can_create=True, can_edit=True, can_delete=True)

        self.user = User.objects.create_user(username="998774578407", password="password1447")
        self.emp = Employee.objects.create(
            user=self.user,
            role=self.role,
            branch=self.branch,
            name="Admin Xodim",
            phone="998774578407",
            is_active=True
        )
        self.emp.set_pin("1447")

        # Warehouse & Inventory Product
        self.inv_cat = InventoryCategory.objects.create(name="Go'sht mahsulotlari")
        self.wh = Warehouse.objects.create(name="Asosiy ombor", branch=self.branch)
        self.inv_meat = InventoryProduct.objects.create(
            name="Mol go'shti (laxtak)",
            barcode="INV-MOL-01",
            category=self.inv_cat,
            unit="kg",
            warehouse=self.wh,
            purchase_price=Decimal("85000.00"),
            current_stock=Decimal("50.000"),
            min_stock=Decimal("5.000")
        )

        # Department & Dish with BOM
        self.dept = Department.objects.create(name="Issiq taomlar", filial=self.branch)
        self.cat = ProductCategory.objects.create(name="Milliy Taomlar", order=1)
        self.dish = Product.objects.create(
            name="Palov Maxsus",
            category=self.cat,
            department=self.dept,
            price=Decimal("45000.00"),
            cost_price=Decimal("25000.00"),
            is_active=True
        )
        ProductIngredient.objects.create(
            product=self.dish,
            maxsulot=self.inv_meat,
            amount=Decimal("0.250"),
            unit="kg"
        )

        # Table
        self.table = Table.objects.create(name="Stol #1", branch=self.branch, status="free", is_active=True)

        # Finance account & category
        self.acc = FinanceAccount.objects.create(name="Asosiy Kassa (Naqd)", account_type="CASH", balance=Decimal("1000000.00"), branch=self.branch)
        self.fin_cat = FinanceCategory.objects.create(name="Taomlar Sotuvidan Tushum", category_type="INCOME")

    def test_01_phone_password_login_and_me(self):
        resp = self.client.post('/employee/auth/login/', data=json.dumps({
            "phone": "998774578407",
            "password": "password1447"
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        token = resp.json()["token"]
        self.assertTrue(len(token) > 0)

        # /employee/auth/me/
        me_resp = self.client.get('/employee/auth/me/', HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["phone"], "998774578407")
        self.assertTrue(me_resp.json()["pin_is_set"])

    def test_02_pin_login(self):
        resp = self.client.post('/employee/auth/pin-login/', data=json.dumps({
            "phone": "998774578407",
            "quick_pin": "1447"
        }), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.json())

    def test_03_settings_and_tables(self):
        resp = self.client.get('/sozlamalar/branches/')
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

        t_resp = self.client.get(f'/table/table/?branch_id={self.branch.id}')
        self.assertEqual(t_resp.status_code, 200)
        data = t_resp.json()
        items = data if isinstance(data, list) else data.get("results", [])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "Stol #1")

    def test_04_full_pos_order_lifecycle(self):
        # 1. Create order for table #1
        order_resp = self.client.post('/order/orders/', data=json.dumps({
            "table": self.table.id,
            "branch": self.branch.id,
            "order_type": "dine_in",
            "guests_count": 2
        }), content_type="application/json")
        self.assertEqual(order_resp.status_code, 201)
        order_id = order_resp.json()["id"]

        # Table should be busy
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, "busy")

        # 2. Add 2 portions of Palov
        item_resp = self.client.post('/order/order-items/', data=json.dumps({
            "order": order_id,
            "product": self.dish.id,
            "quantity": 2,
            "price": "45000.00"
        }), content_type="application/json")
        self.assertEqual(item_resp.status_code, 201)

        # 3. Send to kitchen
        send_resp = self.client.post(f'/order/orders/{order_id}/send_to_kitchen/')
        self.assertEqual(send_resp.status_code, 200)
        self.assertEqual(send_resp.json()["order"]["status"], "sent_to_kitchen")

        # 4. Apply 10% discount
        disc_resp = self.client.post(f'/order/orders/{order_id}/discount/', data=json.dumps({
            "type": "percent",
            "value": 10
        }), content_type="application/json")
        self.assertEqual(disc_resp.status_code, 200)
        # Base was 90,000, 10% discount = 9,000 -> after discount = 81,000, service 10% = 8,100 -> total = 89,100
        self.assertEqual(Decimal(str(disc_resp.json()["order"]["total_amount"])), Decimal("89100.00"))

        # 5. Mark paid (Checkout & Pay)
        pay_resp = self.client.post(f'/order/orders/{order_id}/mark_paid/', data=json.dumps({
            "payment_type": "cash",
            "account_id": self.acc.id
        }), content_type="application/json")
        self.assertEqual(pay_resp.status_code, 200)
        self.assertEqual(pay_resp.json()["order"]["status"], "paid")

        # Table should be freed automatically
        self.table.refresh_from_db()
        self.assertEqual(self.table.status, "free")

        # Meat stock should have been deducted: 50.000 - (2 * 0.250) = 49.500
        self.inv_meat.refresh_from_db()
        self.assertEqual(self.inv_meat.current_stock, Decimal("49.500"))

        # Finance account balance should have increased: 1,000,000 + 89,100 = 1,089,100
        self.acc.refresh_from_db()
        self.assertEqual(self.acc.balance, Decimal("1089100.00"))

        # Finance transaction should be logged
        tx = FinanceTransaction.objects.filter(account=self.acc).first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, Decimal("89100.00"))
        self.assertEqual(tx.transaction_type, "INCOME")

    def test_05_dashboard_and_analytics_kpis(self):
        # Create a paid order to populate analytics
        order = Order.objects.create(
            branch=self.branch,
            table=self.table,
            status="paid",
            payment_type="cash",
            total_amount=Decimal("90000.00")
        )
        OrderItem.objects.create(order=order, product=self.dish, qty=2, unit_price=Decimal("45000.00"))

        # Dashboard Live View
        resp = self.client.get(f'/kitchen/dashboard-live/?branch_id={self.branch.id}')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("jonli_holat", data)
        self.assertIn("haftalik_tushum", data)
        self.assertIn("top_taomlar", data)
        self.assertIn("kategoriya_ulushi", data)

        # Reports endpoints
        r1 = self.client.get(f'/kitchen/umumiy-hisobot/?branch_id={self.branch.id}')
        self.assertEqual(r1.status_code, 200)

        r2 = self.client.get(f'/kitchen/sotuv-hisoboti/?branch_id={self.branch.id}')
        self.assertEqual(r2.status_code, 200)

        r3 = self.client.get(f'/kitchen/abc-analysis/?branch_id={self.branch.id}')
        self.assertEqual(r3.status_code, 200)
        self.assertTrue(isinstance(r3.json(), list) or "abc_analiz" in r3.json())
