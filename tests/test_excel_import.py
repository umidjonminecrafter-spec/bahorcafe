import io
import openpyxl
from decimal import Decimal
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.sozlamalar.models import Branch
from apps.inventory.models import (
    Warehouse, InventoryCategory, Supplier, InventoryProduct,
    Purchase, PurchaseItem, InventoryStockHistory
)
from apps.table.models import Product, ProductCategory
from apps.kitchen.models import Department

class ExcelImportTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = Branch.objects.create(name="Bahor Cafe", city="Farg'ona")
        self.warehouse = Warehouse.objects.create(branch=self.branch, name="Asosiy ombor")
        self.supplier = Supplier.objects.create(name="Agro Meat MCHJ", phone="+998901234567")
        self.department = Department.objects.create(name="Oshxona", filial=self.branch)

    def _create_sample_excel_file(self, headers, rows):
        """Helper to create in-memory .xlsx file."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Mahsulotlar"
        ws.append(headers)
        for r in rows:
            ws.append(r)
        
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        return bio.getvalue()

    def test_edi_import_excel_xlsx_success(self):
        """Test uploading .xlsx file to /inventory/edi-import/"""
        headers = [
            "Tovar nomi", "Kategoriya", "Birligi", "Shtrixkod", "MXIK kodi",
            "Kelish narxi", "Sotish narxi", "Miqdori", "Min limit"
        ]
        rows = [
            ["Mol go'shti (lahm)", "Go'sht mahsulotlari", "kg", "4780012345678", "0123456789", "85 000 so'm", "100 000", "25.5", "5"],
            ["Piyoz sariq", "Sabzavotlar", "kg", "4780012345679", "0123456790", "3 500", "5 000", "100", "20"],
            ["Coca-Cola 1.5L", "Ichimliklar", "dona", "5449000000996", "0123456791", "12 000", "15 000", "50", "10"]
        ]
        content = self._create_sample_excel_file(headers, rows)
        file_obj = SimpleUploadedFile("faktura.xlsx", content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        res = self.client.post('/inventory/edi-import/', {'file': file_obj, 'supplier_id': self.supplier.id}, format='multipart')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'success')
        self.assertEqual(res.data['imported_rows'], 3)
        self.assertEqual(res.data['created_count'], 3)

        # Check DB
        meat = InventoryProduct.objects.filter(name="Mol go'shti (lahm)").first()
        self.assertIsNotNone(meat)
        self.assertEqual(meat.purchase_price, Decimal('85000.00'))
        self.assertEqual(meat.selling_price, Decimal('100000.00'))
        self.assertEqual(meat.current_stock, Decimal('25.500'))
        self.assertEqual(meat.barcode, "4780012345678")
        self.assertEqual(meat.category.name, "Go'sht mahsulotlari")

        # Check Purchase record was created
        purchase_id = res.data.get('purchase_id')
        self.assertIsNotNone(purchase_id)
        purchase = Purchase.objects.filter(id=purchase_id).first()
        self.assertIsNotNone(purchase)
        self.assertEqual(purchase.items.count(), 3)
        self.assertTrue(purchase.total_amount > Decimal('0.0'))

        # Check stock history logged
        hist = InventoryStockHistory.objects.filter(product=meat, movement_type='in').first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.quantity, Decimal('25.500'))

    def test_import_existing_product_updates_stock_and_price(self):
        """Test that importing existing product adds to stock and updates price"""
        prod = InventoryProduct.objects.create(
            warehouse=self.warehouse,
            name="Shakar",
            unit="kg",
            barcode="4780099999999",
            purchase_price=Decimal('10000.0'),
            selling_price=Decimal('12000.0'),
            current_stock=Decimal('10.0')
        )

        headers = ["Nomi", "Shtrixkod", "Kelish narxi", "Sotish narxi", "Miqdor"]
        rows = [
            ["Shakar", "4780099999999", "11 000", "14 000", "20.0"]
        ]
        content = self._create_sample_excel_file(headers, rows)
        file_obj = SimpleUploadedFile("kirim.xlsx", content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        res = self.client.post('/inventory/products/import/', {'file': file_obj}, format='multipart')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['updated_count'], 1)
        self.assertEqual(res.data['created_count'], 0)

        prod.refresh_from_db()
        self.assertEqual(prod.purchase_price, Decimal('11000.00'))
        self.assertEqual(prod.selling_price, Decimal('14000.00'))
        self.assertEqual(prod.current_stock, Decimal('30.000')) # 10 + 20

    def test_import_csv_file_with_semicolons(self):
        """Test uploading CSV file with semicolon delimiter"""
        csv_data = (
            "nomi;kategoriya;birlik;kelish_narxi;sotish_narxi;miqdor\n"
            "Guruch Alanga;Don mahsulotlari;kg;18000;22000;50\n"
            "Yog' paxta;Yog'lar;litr;16000;19000;30\n"
        ).encode('utf-8')
        file_obj = SimpleUploadedFile("tovarlar.csv", csv_data, content_type="text/csv")

        res = self.client.post('/inventory/edi-import/', {'file': file_obj}, format='multipart')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['imported_rows'], 2)

        rice = InventoryProduct.objects.filter(name="Guruch Alanga").first()
        self.assertIsNotNone(rice)
        self.assertEqual(rice.current_stock, Decimal('50.000'))
        self.assertEqual(rice.purchase_price, Decimal('18000.00'))

    def test_import_json_payload(self):
        """Test sending direct JSON array to import endpoint"""
        payload = {
            "warehouse_id": self.warehouse.id,
            "items": [
                {
                    "nomi": "Tuz osh",
                    "kategoriya": "Ziravorlar",
                    "birligi": "pachka",
                    "kelish_narxi": 2000,
                    "sotish_narxi": 3000,
                    "miqdor": 40
                }
            ]
        }
        res = self.client.post('/inventory/products/import-excel/', payload, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['imported_rows'], 1)

        tuz = InventoryProduct.objects.filter(name="Tuz osh").first()
        self.assertIsNotNone(tuz)
        self.assertEqual(tuz.current_stock, Decimal('40.000'))

    def test_menu_dishes_excel_import(self):
        """Test bulk importing dishes / menu items to /table/products/import/"""
        headers = ["Taom nomi", "Kategoriya", "Bo'lim", "Narxi", "Tannarx", "Birlik", "MXIK"]
        rows = [
            ["Osh Choyxona", "Milliy taomlar", "Oshxona", "45 000", "28 000", "porsiya", "999888111"],
            ["Manti 5 dona", "Milliy taomlar", "Oshxona", "35 000", "20 000", "porsiya", "999888112"],
            ["Limon choy", "Ichimliklar", "Bar", "15 000", "5 000", "choynak", "999888113"]
        ]
        content = self._create_sample_excel_file(headers, rows)
        file_obj = SimpleUploadedFile("menu.xlsx", content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        res = self.client.post('/table/products/import/', {'file': file_obj}, format='multipart')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['imported_rows'], 3)
        self.assertEqual(res.data['created_count'], 3)

        osh = Product.objects.filter(name="Osh Choyxona").first()
        self.assertIsNotNone(osh)
        self.assertEqual(osh.price, Decimal('45000.00'))
        self.assertEqual(osh.cost_price, Decimal('28000.00'))
        self.assertEqual(osh.category.name, "Milliy taomlar")
        self.assertEqual(osh.department.name, "Oshxona")
        self.assertEqual(osh.mxik, "999888111")

        # Test kitchen alias route /kitchen/foods/import/
        file_obj2 = SimpleUploadedFile("menu2.xlsx", content, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        res_kitchen = self.client.post('/kitchen/foods/import/', {'file': file_obj2}, format='multipart')
        self.assertEqual(res_kitchen.status_code, 200)
        self.assertEqual(res_kitchen.data['updated_count'], 3)

    def test_empty_file_returns_error_safely(self):
        """Test sending empty request or empty file returns 400 Bad Request safely without 500 error"""
        res = self.client.post('/inventory/edi-import/', {}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['status'], 'error')

        empty_file = SimpleUploadedFile("empty.xlsx", b"", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        res2 = self.client.post('/inventory/edi-import/', {'file': empty_file}, format='multipart')
        self.assertEqual(res2.status_code, 400)
        self.assertEqual(res2.data['status'], 'error')
