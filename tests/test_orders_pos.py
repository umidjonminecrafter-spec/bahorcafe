from django.test import TestCase
from rest_framework.test import APIClient
from decimal import Decimal
from apps.sozlamalar.models import Branch, TaxSettings
from apps.employee.models import Employee, Role
from apps.table.models import Table, Product, ProductCategory, ProductIngredient
from apps.inventory.models import InventoryProduct, InventoryCategory, Warehouse
from apps.order.models import Order, OrderItem

class OrderPOSTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = Branch.objects.create(name="Bahor Cafe")
        TaxSettings.objects.create(branch=self.branch, tax_percent=Decimal('0.0'), service_percent=Decimal('10.0'))
        
        self.table = Table.objects.create(branch=self.branch, name="1-stol", status="free")
        self.cat = ProductCategory.objects.create(name="Taomlar")
        self.prod = Product.objects.create(name="Palov", category=self.cat, price=Decimal('40000.0'), cost_price=Decimal('20000.0'))
        
        self.inv_cat = InventoryCategory.objects.create(name="Go'sht")
        self.wh = Warehouse.objects.create(name="Asosiy", branch=self.branch)
        self.raw_mat = InventoryProduct.objects.create(
            name="Mol go'shti", category=self.inv_cat, warehouse=self.wh,
            unit="kg", purchase_price=Decimal('80000.0'), current_stock=Decimal('10.0')
        )
        ProductIngredient.objects.create(product=self.prod, maxsulot=self.raw_mat, amount=Decimal('0.200'), unit="kg")

    def test_create_order_and_mark_paid(self):
        # Create order
        res = self.client.post('/order/orders/', {
            'branch': self.branch.id,
            'table': self.table.id,
            'type': 'dine_in',
            'items_data': [
                {'product': self.prod.id, 'qty': 2, 'unit_price': 40000}
            ]
        }, format='json')
        self.assertEqual(res.status_code, 201)
        order_id = res.data['id']
        
        # Check subtotal and total calculation (2 * 40000 = 80000 + 10% service = 88000)
        self.assertEqual(float(res.data['base_amount']), 80000.0)
        self.assertEqual(float(res.data['service_amount']), 8000.0)
        self.assertEqual(float(res.data['total_amount']), 88000.0)
        
        # Table should be busy
        self.table.refresh_from_db()
        self.assertTrue(self.table.is_busy)

        # Mark paid
        pay_res = self.client.post(f'/order/orders/{order_id}/mark_paid/', {
            'payment_type': 'cash',
            'cash_amount': 88000
        }, format='json')
        self.assertEqual(pay_res.status_code, 200)

        # Table should be free
        self.table.refresh_from_db()
        self.assertFalse(self.table.is_busy)
        self.assertEqual(self.table.status, 'free')

        # Raw material should be deducted (10.0 - 2 * 0.200 = 9.600)
        self.raw_mat.refresh_from_db()
        self.assertEqual(self.raw_mat.current_stock, Decimal('9.600'))
