import os
import sys
import django
from decimal import Decimal
from datetime import timedelta

# Setup django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bahor_backend.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.sozlamalar.models import Branch, RestaurantSettings, TaxSettings, ReceiptSettings, OrderFlowSettings
from apps.employee.models import Role, RoleModulePermission, Employee, EmployeePermission, SalaryScheme, SalaryRecord
from apps.table.models import Table, TablePart, TableLayout, ProductCategory, Product, ProductIngredient
from apps.kitchen.models import Department, SemiProduct, SemiProductIngredient
from apps.inventory.models import (
    Warehouse, InventoryCategory, Unit, Supplier, InventoryProduct,
    Purchase, PurchaseItem, Realization, RealizationItem, InventoryStockHistory
)
from apps.order.models import Order, OrderItem
from apps.finance.models import FinanceAccount, FinanceCategory, FinanceTransaction

def seed():
    print("🌱 Seeding database with initial data...")

    # 1. Branch
    branch, _ = Branch.objects.get_or_create(
        id=1,
        defaults={
            'name': 'Bahor Cafe',
            'city': "Farg'ona",
            'address': "Mustaqillik ko'chasi 45",
            'phone': "+998 77 457 84 07",
            'is_active': True
        }
    )

    # 2. Settings
    RestaurantSettings.objects.get_or_create(
        branch=branch,
        defaults={
            'name': 'Bahor Cafe',
            'address': "Toshkent sh., Mustaqillik ko'chasi 45",
            'phone': "+998 77 457 84 07",
            'description': "Milliy va yevropa taomlari restorani"
        }
    )

    TaxSettings.objects.get_or_create(
        branch=branch,
        defaults={
            'tax_percent': Decimal('0.0'),
            'service_percent': Decimal('10.0'),
            'calculation_type': 'auto'
        }
    )

    ReceiptSettings.objects.get_or_create(
        branch=branch,
        defaults={
            'cafe_name': 'Bahor Cafe',
            'address': "Mustaqillik ko'chasi 45",
            'phone': "+998 77 457 84 07",
            'footer_text': "Xaridingiz uchun rahmat! Yana kutib qolamiz!"
        }
    )

    OrderFlowSettings.objects.get_or_create(
        branch=branch,
        defaults={
            'auto_kitchen': True,
            'signal': True,
            'bill_btn': True,
            'served': False
        }
    )

    # 3. Roles & Permissions
    all_modules = [
        'dashboard', 'analytics', 'staff', 'settings', 'set_restoran',
        'set_soliq', 'set_chek', 'set_buyurtma', 'security', 'menu',
        'ombor', 'stock_ombor', 'stock_kirim', 'stock_chiqim', 'stock_tarix',
        'kassa', 'kitchen', 'waiter', 'finance', 'restaurant'
    ]

    admin_role, _ = Role.objects.get_or_create(
        name='ADMIN',
        defaults={'salary_type': 'fixed', 'salary_amount': Decimal('8000000.0')}
    )
    for m in all_modules:
        RoleModulePermission.objects.get_or_create(
            role=admin_role, module=m,
            defaults={'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': True}
        )

    cashier_role, _ = Role.objects.get_or_create(
        name='CASHIER',
        defaults={'salary_type': 'fixed', 'salary_amount': Decimal('4500000.0')}
    )
    for m in ['dashboard', 'kassa', 'orders', 'menu', 'waiter', 'finance']:
        RoleModulePermission.objects.get_or_create(
            role=cashier_role, module=m,
            defaults={'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False}
        )

    waiter_role, _ = Role.objects.get_or_create(
        name='WAITER',
        defaults={'salary_type': 'foizli', 'salary_amount': Decimal('5.0')}
    )
    for m in ['waiter', 'kassa', 'menu']:
        RoleModulePermission.objects.get_or_create(
            role=waiter_role, module=m,
            defaults={'can_view': True, 'can_create': True, 'can_edit': False, 'can_delete': False}
        )

    kitchen_role, _ = Role.objects.get_or_create(
        name='KITCHEN',
        defaults={'salary_type': 'fixed', 'salary_amount': Decimal('6000000.0')}
    )
    for m in ['kitchen', 'menu', 'ombor']:
        RoleModulePermission.objects.get_or_create(
            role=kitchen_role, module=m,
            defaults={'can_view': True, 'can_create': True, 'can_edit': True, 'can_delete': False}
        )

    # 4. Users / Employees
    # Primary Admin User (phone: 998774578407, pass: 1447, pin: 1447)
    admin_user, _ = User.objects.get_or_create(username='998774578407')
    admin_user.set_password('1447')
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()
    Token.objects.get_or_create(user=admin_user)

    admin_emp, _ = Employee.objects.get_or_create(
        phone='998774578407',
        defaults={
            'user': admin_user,
            'name': 'Admin Xodim',
            'role': admin_role,
            'branch': branch,
            'is_active': True,
        }
    )
    admin_emp.set_pin('1447')
    admin_emp.save()

    # Also make sure 1111 works for quick testing
    test_user, _ = User.objects.get_or_create(username='admin')
    test_user.set_password('1447')
    test_user.save()

    # Waiter employee
    w_user, _ = User.objects.get_or_create(username='998901112233')
    w_user.set_password('1234')
    w_user.save()
    Token.objects.get_or_create(user=w_user)

    waiter_emp, _ = Employee.objects.get_or_create(
        phone='998901112233',
        defaults={
            'user': w_user,
            'name': 'Alisher Ofitsiant',
            'role': waiter_role,
            'branch': branch,
            'is_active': True,
        }
    )
    waiter_emp.set_pin('1234')
    waiter_emp.save()

    # 5. Units & Inventory
    units = ['kg', 'dona', 'litr', 'gramm', 'ml', 'portsiya', 'qadoq']
    for u in units:
        Unit.objects.get_or_create(name=u, defaults={'short_name': u})

    main_wh, _ = Warehouse.objects.get_or_create(name="Asosiy ombor", defaults={'branch': branch})
    kitchen_wh, _ = Warehouse.objects.get_or_create(name="Oshxona ombori", defaults={'branch': branch})

    inv_cat_meat, _ = InventoryCategory.objects.get_or_create(name="Go'sht mahsulotlari")
    inv_cat_veg, _ = InventoryCategory.objects.get_or_create(name="Sabzavotlar va Mevalar")
    inv_cat_bev, _ = InventoryCategory.objects.get_or_create(name="Ichimliklar")
    inv_cat_dry, _ = InventoryCategory.objects.get_or_create(name="Don va un mahsulotlari")

    supplier1, _ = Supplier.objects.get_or_create(name="Agro Meat MCHJ", defaults={'phone': "+998901230001", 'company': "Agro Meat"})
    supplier2, _ = Supplier.objects.get_or_create(name="Dehqon Bozor Ta'minoti", defaults={'phone': "+998901230002", 'company': "Dehqon Bozor"})

    raw_items = [
        {"name": "Mol go'shti (lahm)", "cat": inv_cat_meat, "unit": "kg", "cost": 85000, "stock": 65.0},
        {"name": "Qo'y go'shti (lahm)", "cat": inv_cat_meat, "unit": "kg", "cost": 95000, "stock": 45.0},
        {"name": "Guruch (Lazer)", "cat": inv_cat_dry, "unit": "kg", "cost": 28000, "stock": 100.0},
        {"name": "Piyoz", "cat": inv_cat_veg, "unit": "kg", "cost": 3500, "stock": 120.0},
        {"name": "Sabzi (sariq)", "cat": inv_cat_veg, "unit": "kg", "cost": 4000, "stock": 90.0},
        {"name": "O'simlik yog'i (paxta)", "cat": inv_cat_dry, "unit": "litr", "cost": 18000, "stock": 60.0},
        {"name": "Coca-Cola 1.5L", "cat": inv_cat_bev, "unit": "dona", "cost": 11000, "sell": 16000, "stock": 150.0},
        {"name": "Fanta 1.5L", "cat": inv_cat_bev, "unit": "dona", "cost": 11000, "sell": 16000, "stock": 100.0},
        {"name": "Ko'k choy (qadoq)", "cat": inv_cat_dry, "unit": "kg", "cost": 35000, "stock": 20.0},
        {"name": "Tandir non", "cat": inv_cat_dry, "unit": "dona", "cost": 3000, "sell": 5000, "stock": 80.0},
    ]

    saved_raw = {}
    for r in raw_items:
        prod, _ = InventoryProduct.objects.get_or_create(
            name=r['name'],
            defaults={
                'category': r['cat'],
                'warehouse': main_wh,
                'unit': r['unit'],
                'purchase_price': Decimal(str(r['cost'])),
                'selling_price': Decimal(str(r.get('sell', r['cost'] * 1.3))),
                'current_stock': Decimal(str(r['stock'])),
                'min_stock': Decimal('10.0'),
                'max_stock': Decimal('200.0'),
                'is_active': True
            }
        )
        saved_raw[r['name']] = prod

    # 6. Departments & Menu Categories & Products
    dep_kitchen, _ = Department.objects.get_or_create(name="Oshxona", defaults={'ombor': kitchen_wh, 'filial': branch})
    dep_bar, _ = Department.objects.get_or_create(name="Bar", defaults={'ombor': main_wh, 'filial': branch})
    dep_shashlik, _ = Department.objects.get_or_create(name="Shashlik", defaults={'ombor': kitchen_wh, 'filial': branch})

    m_cat_main, _ = ProductCategory.objects.get_or_create(name="Asosiy Taomlar", defaults={'order': 1})
    m_cat_shashlik, _ = ProductCategory.objects.get_or_create(name="Shashliklar", defaults={'order': 2})
    m_cat_salad, _ = ProductCategory.objects.get_or_create(name="Salatlar", defaults={'order': 3})
    m_cat_drink, _ = ProductCategory.objects.get_or_create(name="Ichimliklar", defaults={'order': 4})
    m_cat_bread, _ = ProductCategory.objects.get_or_create(name="Non va un mahsulotlari", defaults={'order': 5})

    menu_items = [
        {
            "name": "Bahor Oshi (Choyxona palov)", "cat": m_cat_main, "dep": dep_kitchen,
            "price": 45000, "cost": 22000, "unit": "portsiya",
            "recipe": [
                ("Mol go'shti (lahm)", 0.15),
                ("Guruch (Lazer)", 0.15),
                ("Sabzi (sariq)", 0.15),
                ("Piyoz", 0.05),
                ("O'simlik yog'i (paxta)", 0.04)
            ]
        },
        {
            "name": "Qo'y go'shti shashlik (Kuskavoy)", "cat": m_cat_shashlik, "dep": dep_shashlik,
            "price": 22000, "cost": 12000, "unit": "dona",
            "recipe": [
                ("Qo'y go'shti (lahm)", 0.12),
                ("Piyoz", 0.02)
            ]
        },
        {
            "name": "Lula Kabob", "cat": m_cat_shashlik, "dep": dep_shashlik,
            "price": 18000, "cost": 9500, "unit": "dona",
            "recipe": [
                ("Mol go'shti (lahm)", 0.10),
                ("Piyoz", 0.03)
            ]
        },
        {
            "name": "Achichuk salati", "cat": m_cat_salad, "dep": dep_kitchen,
            "price": 12000, "cost": 4000, "unit": "portsiya",
            "recipe": [("Piyoz", 0.08)]
        },
        {
            "name": "Coca-Cola 1.5L", "cat": m_cat_drink, "dep": dep_bar,
            "price": 16000, "cost": 11000, "unit": "dona",
            "recipe": [("Coca-Cola 1.5L", 1.0)]
        },
        {
            "name": "Ko'k choy (choynak)", "cat": m_cat_drink, "dep": dep_bar,
            "price": 5000, "cost": 1000, "unit": "choynak",
            "recipe": [("Ko'k choy (qadoq)", 0.02)]
        },
        {
            "name": "Tandir non", "cat": m_cat_bread, "dep": dep_kitchen,
            "price": 5000, "cost": 3000, "unit": "dona",
            "recipe": [("Tandir non", 1.0)]
        }
    ]

    saved_products = []
    for m in menu_items:
        prod, _ = Product.objects.get_or_create(
            name=m['name'],
            defaults={
                'category': m['cat'],
                'department': m['dep'],
                'price': Decimal(str(m['price'])),
                'cost_price': Decimal(str(m['cost'])),
                'unit': m['unit'],
                'is_active': True
            }
        )
        saved_products.append(prod)
        for r_name, amt in m['recipe']:
            if r_name in saved_raw:
                ProductIngredient.objects.get_or_create(
                    product=prod,
                    maxsulot=saved_raw[r_name],
                    defaults={'amount': Decimal(str(amt)), 'unit': saved_raw[r_name].unit}
                )

    # 7. Tables
    table_names = ["1-stol", "2-stol", "3-stol", "4-stol", "5-stol", "6-stol", "VIP 1", "VIP 2", "Teras 1", "Teras 2"]
    saved_tables = []
    for i, t_name in enumerate(table_names, 1):
        tbl, _ = Table.objects.get_or_create(
            name=t_name,
            defaults={
                'branch': branch,
                'table_number': i,
                'status': 'free',
                'is_busy': False,
                'is_active': True
            }
        )
        saved_tables.append(tbl)
        TablePart.objects.get_or_create(table=tbl, name="Asosiy zal")

    # 8. Finance Accounts & Categories
    acc_cash, _ = FinanceAccount.objects.get_or_create(
        name="Asosiy naqd kassa",
        defaults={'branch': branch, 'account_type': 'CASH', 'balance': Decimal('15000000.0')}
    )
    acc_card, _ = FinanceAccount.objects.get_or_create(
        name="Terminal (Humo/Uzcard)",
        defaults={'branch': branch, 'account_type': 'NON_CASH', 'balance': Decimal('8500000.0')}
    )
    acc_bank, _ = FinanceAccount.objects.get_or_create(
        name="Bank hisob raqami",
        defaults={'branch': branch, 'account_type': 'BANK', 'balance': Decimal('25000000.0')}
    )

    f_cat_sales, _ = FinanceCategory.objects.get_or_create(name="Sotuv tushumi", defaults={'category_type': 'INCOME'})
    f_cat_purchase, _ = FinanceCategory.objects.get_or_create(name="Ombor xaridi", defaults={'category_type': 'EXPENSE'})
    f_cat_salary, _ = FinanceCategory.objects.get_or_create(name="Xodimlar maoshi", defaults={'category_type': 'EXPENSE'})
    f_cat_rent, _ = FinanceCategory.objects.get_or_create(name="Ijara to'lovi", defaults={'category_type': 'EXPENSE'})

    # 9. Create Sample Orders for Past 7 Days
    now = timezone.now()
    order_num = 1001

    for day_offset in range(6, -1, -1):
        dt = now - timedelta(days=day_offset, hours=2)
        # Create 3-5 orders per day
        for ord_idx in range(3):
            tbl = saved_tables[ord_idx % len(saved_tables)]
            order = Order.objects.create(
                number=order_num,
                branch=branch,
                table=tbl,
                assigned_waiter=waiter_emp,
                type='dine_in',
                status='paid',
                guests_count=2 + ord_idx,
                service_percent=Decimal('10.0'),
                payment_type='cash' if ord_idx % 2 == 0 else 'card',
                opened_at=dt,
                paid_at=dt + timedelta(minutes=45),
                closed_at=dt + timedelta(minutes=50)
            )
            order_num += 1

            # Add items
            p1 = saved_products[0] # Osh
            p2 = saved_products[1] # Shashlik
            p3 = saved_products[4] # Cola

            OrderItem.objects.create(order=order, product=p1, qty=Decimal('2.0'), unit_price=p1.price, cost_price=p1.cost_price, status='served')
            OrderItem.objects.create(order=order, product=p2, qty=Decimal('4.0'), unit_price=p2.price, cost_price=p2.cost_price, status='served')
            OrderItem.objects.create(order=order, product=p3, qty=Decimal('1.0'), unit_price=p3.price, cost_price=p3.cost_price, status='served')

            order.recalculate_totals()
            order.created_at = dt
            order.save(update_fields=['created_at'])

            # Finance Transaction
            FinanceTransaction.objects.create(
                branch=branch,
                account=acc_cash if order.payment_type == 'cash' else acc_card,
                category=f_cat_sales,
                transaction_type='INCOME',
                payment_type=order.payment_type,
                amount=order.total_amount,
                source='kassa',
                order=order,
                employee=waiter_emp,
                description=f"Buyurtma #{order.number} to'lovi",
                date=dt.date()
            )

    print("✅ Database seeding completed successfully!")
    print(f"   Admin Phone: 998774578407 (Password: 1447, PIN: 1447)")
    print(f"   Waiter Phone: 998901112233 (Password: 1234, PIN: 1234)")
    print(f"   Products: {Product.objects.count()} dishes, {InventoryProduct.objects.count()} inventory raw materials")
    print(f"   Tables: {Table.objects.count()} tables")
    print(f"   Sample Orders: {Order.objects.count()} orders with transactions")

if __name__ == '__main__':
    seed()
