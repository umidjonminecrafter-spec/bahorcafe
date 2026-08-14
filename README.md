# 🍽️ Bahor Cafe - Backend API & Boshqaruv Tizimi

Bahor Cafe restorani, oshxona, ombor, POS, moliya va xodimlar boshqaruvi uchun to‘liq Django REST Framework asosidagi backend tizimi.

---

## 🚀 Ishga Tushirish va O‘rnatish

### 1. Talablar
- Python 3.10+
- Virtual Environment (`venv`)

### 2. O‘rnatish va Virtual Muhit
```bash
# Virtual muhit yaratish va faollashtirish
python3 -m venv venv
source venv/bin/activate

# Kutubxonalarni o‘rnatish
pip install -r requirements.txt
```

### 3. Migratsiyalar va Dastlabki Ma'lumotlar
```bash
# Migratsiyalarni qo‘llash
python manage.py migrate

# Dastlabki test/demo ma'lumotlarni yuklash (ixtiyoriy)
python seed_data.py
```

### 4. Serverni Ishga Tushirish
```bash
python manage.py runserver
```

---

## 📌 Barcha Backend API Endpointlarining To‘liq va Tartiblangan Ro‘yxati

### Umumiy Qoidalar:
- **Base URL:** `http://127.0.0.1:8000` (yoki server domeni)
- **Header:** `Authorization: Token <token_qiymati>`
- **Content-Type:** `application/json`
- **Swagger / Interaktiv Docs:** `http://127.0.0.1:8000/api/docs/`
- **ReDoc:** `http://127.0.0.1:8000/api/redoc/`
- **OpenAPI Schema (JSON):** `http://127.0.0.1:8000/api/schema/`

---

### 1. 👤 Autentifikatsiya va Profil (`/employee/auth/`)

| Method | Endpoint | Qaysi sahifa / Vazifasi | Body / Parametrlar |
|---|---|---|---|
| **POST** | `/employee/auth/login/` | Login sahifasi (Telefon + Parol) | `{"phone": "998774578407", "password": "1447"}` |
| **POST** | `/employee/auth/pin-login/` | Tezkor PIN kirish (4 xonali PIN) | `{"phone": "998774578407", "quick_pin": "1447"}` |
| **POST** | `/employee/auth/set-pin/` | PIN o‘zgartirish / o‘rnatish | `{"quick_pin": "1447", "confirm_pin": "1447"}` |
| **GET** | `/employee/auth/me/` | Joriy foydalanuvchi ma'lumotlari & huquqlari | — (Headerda `Authorization: Token ...` talab etiladi) |
| **POST** | `/employee/auth/logout/` | Tizimdan chiqish | — |

---

### 2. 👥 Xodimlar, Rollar va Ish haqi (`/employee/`)

| Method | Endpoint | Qaysi sahifa / Vazifasi | Izoh |
|---|---|---|---|
| **GET / POST** | `/employee/employees/` | Xodimlar ro‘yxati & Yangi xodim qo‘shish | `name`, `phone`, `role`, `branch` |
| **GET / PATCH / DELETE** | `/employee/employees/{id}/` | Xodimni tahrirlash / o‘chirish | — |
| **GET / POST** | `/employee/roles/` | Rollar ro‘yxati (Admin, Ofitsiant, Oshpaz...) | `name`, `salary_type`, `salary_amount` |
| **GET / PATCH / DELETE** | `/employee/roles/{id}/` | Rolni tahrirlash / o‘chirish | — |
| **GET / POST** | `/employee/role-permissions/` | Rollar huquqlari matritsasi | `role`, `module`, `can_view`, `can_edit`... |
| **GET / POST** | `/employee/salary-schemes/` | Oylik ish haqi sozlamalari | `fiksa`, `foizli`, `soatlik`, `fiksa_foiz`, `smena`, `ball` |
| **GET / POST** | `/employee/salary-records/` | Berilgan oyliklar / avanslar tarixi | Xodimga to‘langan summa va sana |
| **POST** | `/employee/salary/simulate/` | Oylik hisob-kitob simulyatori | Smenalar va sotuv foizini avto hisoblaydi |

---

### 3. ⚙️ Sozlamalar va Filiallar (`/sozlamalar/` & `/order-flow/`)

| Method | Endpoint | Qaysi sahifa / Vazifasi | Izoh |
|---|---|---|---|
| **GET / POST** | `/sozlamalar/branches/` | Filiallar (Multi-branch) boshqaruvi | `name`, `city`, `address`, `phone` |
| **GET / PATCH / DELETE** | `/sozlamalar/branches/{id}/` | Filialni o‘zgartirish / o‘chirish | — |
| **GET / PATCH** | `/sozlamalar/restaurant-settings/` | Restoran sozlamalari | Nom, manzil, telefon, lokatsiya |
| **GET / PATCH** | `/sozlamalar/tax-settings/` | Soliq va xizmat sozlamalari | `tax_percent`, `service_percent`, `calculation_type` |
| **GET / PATCH** | `/sozlamalar/check-settings/` | Chek printer sozlamalari | Sarlavha, footer yozuvlari, toggle maydonlar |
| **GET / PATCH** | `/sozlamalar/order-flow/` (yoki `/order-flow/`) | Buyurtma jarayoni sozlamalari | `auto_kitchen`, `signal`, `bill_btn`, `served` |

---

### 4. 🍽️ Stollar va Menyular / Taomlar (`/table/`)

| Method | Endpoint | Qaysi sahifa / Vazifasi | Izoh |
|---|---|---|---|
| **GET / POST** | `/table/table/` | Stollar ro‘yxati & Stol qo‘shish | `?branch_id=1` filtri bilan ishlaydi |
| **GET / PATCH / DELETE** | `/table/table/{id}/` | Stol holati (Band/Bo‘sh), nomini o‘zgartirish | `status`: `"free"` / `"busy"` / `"payment"` |
| **GET / POST** | `/table/table-part/` | Stol qismlari (1A, 1B, 1C) | Guruhlangan stollar |
| **GET / POST** | `/table/category/` | Menyu kategoriyalari (Taomlar, Ichimliklar...) | Tartib raqami, ikonka, rasm |
| **GET / PATCH / DELETE** | `/table/category/{id}/` | Kategoriyani tahrirlash / o‘chirish | — |
| **GET / POST** | `/table/product/` | Taomlar / Menyu mahsulotlari ro‘yxati | Narx, tannarx, ustama %, rasm, MXIK |
| **GET / PATCH / DELETE** | `/table/product/{id}/` | Taomni tahrirlash / o‘chirish | — |
| **GET / POST** | `/table/product-ingredients/` | Taom retsepti (BOM) | Taom uchun ketadigan ombor xomashyolari |

---

### 5. 👨🍳 Oshxona, Jonli Dashboard va Analitika (`/kitchen/`)

| Method | Endpoint | Qaysi sahifa / Vazifasi | Izoh |
|---|---|---|---|
| **GET / POST** | `/kitchen/departments/` | Oshxona bo‘limlari (Bar, Somsa, Shashlik...) | Printer va filial biriktirish |
| **GET / POST** | `/kitchen/semi-products/` | Yarim tayyor mahsulotlar (Qiyma, Sous...) | Retsepti va tannarxi |
| **GET / POST** | `/kitchen/foods/` | Oshxona taomlari boshqaruvi | — |
| **GET / POST** | `/kitchen/categories/` | Oshxona kategoriyalari | — |
| **GET** | `/kitchen/dashboard/` (yoki `/kitchen/dashboard-live/`) | Asosiy Dashboard (Bosh sahifa) | Real-vaqt jonli KPIlar, 7 kunlik tushum, Top 5 taomlar |
| **GET** | `/kitchen/sync-status/` | Oflayn sinxronizatsiya tekshiruvi | Bo‘limlar holati |
| **GET** | `/kitchen/umumiy-hisobot/` | Umumiy Hisobot sahifasi | `?branch_id=1&from_date=&to_date=` |
| **GET** | `/kitchen/sotuv-hisoboti/` | Sotuv Hisoboti sahifasi | Taomlar, kategoriyalar kesimida |
| **GET** | `/kitchen/xodimlar-hisoboti/` | Xodimlar Hisoboti sahifasi | Ofitsiantlar faolligi, buyurtmalar soni va tushumi |
| **GET** | `/kitchen/abc-analysis/` | ABC Analiz sahifasi | Pareto 80/20 tahlili (A, B, C guruhlari) |

---

### 6. 📦 Ombor va Zaxiralar Nazorati (`/inventory/`)

| Method | Endpoint | Qaysi sahifa / Vazifasi | Izoh |
|---|---|---|---|
| **GET / POST** | `/inventory/ombor/` (yoki `/inventory/warehouses/`) | Omborlar ro‘yxati (Asosiy, Bar ombor...) | — |
| **GET / POST** | `/inventory/categories/` | Xomashyo kategoriyalari (Go‘sht, Sabzavot...) | — |
| **GET / POST** | `/inventory/unit/` | O‘lchov birliklari (kg, g, l, dona...) | — |
| **GET / POST** | `/inventory/suppliers/` | Yetkazib beruvchilar (Kontragentlar) | Nomi, telefon, kompaniya |
| **GET / POST** | `/inventory/products/` | Xomashyo tovarlari ro‘yxati | Qoldiq, min limit, kelish narxi, shtrixkod |
| **GET / PATCH / DELETE** | `/inventory/products/{id}/` | Xomashyoni tahrirlash / o‘chirish | — |
| **GET / POST** | `/inventory/purchases/` (yoki `/inventory/kirim/`) | Kirim qilish (Mahsulot qabul qilish) | Avtomatik qoldiqni oshiradi va tarixga yozadi |
| **GET / POST** | `/inventory/chiqim/` | Chiqim / Spisaniye qilish | Buzilgan/yaroqsiz tovarlarni hisobdan chiqarish |
| **GET / POST** | `/inventory/realizations/` | Realizatsiya qilish (Optom sotuv) | Ombor tovarlarini realizatsiya qilish |
| **GET** | `/inventory/tarix/` | Harakatlar tarixi (Audit jurnali) | Barcha kirim, chiqim va avto-yechishlar |
| **POST** | `/inventory/edi-import/` | Elektron faktura / Excel import | Tovar ro‘yxatini fayldan yuklash |

---

### 7. 💳 POS, Buyurtmalar, Kassa va Cheklar (`/order/` & `/receipts/`)

| Method | Endpoint | Qaysi sahifa / Vazifasi | Izoh |
|---|---|---|---|
| **GET / POST** | `/order/orders/` | Buyurtmalar ro‘yxati & Yangi buyurtma | `?branch_id=1&table=2&status=open` |
| **GET / PATCH / DELETE** | `/order/orders/{id}/` | Buyurtma tafsilotlari & o‘zgartirish | Mehmonlar soni, ofitsiant biriktirish |
| **POST** | `/order/orders/{id}/send_to_kitchen/` | Oshxonaga yuborish tugmasi | Taomlarni pishirishga o‘tkazadi |
| **POST** | `/order/orders/{id}/discount/` | Chegirma qo‘llash | `{"type": "percent"/"fixed", "value": 10}` |
| **POST** | `/order/orders/{id}/mark_paid/` | To‘lovni qabul qilish & Yopish (Kassa) | Stolni bo‘shatadi, retsept bo‘yicha ombordan yechadi, moliyaga tushumni yozadi |
| **GET / POST** | `/order/order-items/` | Buyurtmaga taom qo‘shish | `order`, `product`, `qty`, `note` |
| **PATCH / DELETE** | `/order/order-items/{id}/` | Taom miqdorini o‘zgartirish / o‘chirish | — |
| **GET** | `/receipts/print/` (yoki `/order/checkout-print/`) | Termal chek & Begunok chop etish | `?order_id=123` |
| **POST** | `/payments/start` | To‘lov jarayonini boshlash | — |
| **GET** | `/order/reports/` | Buyurtmalar analitikasi | Jami tushum va o‘rtacha chek |

---

### 8. 💰 Moliya va Kassa Hisoblari (`/finance/`)

| Method | Endpoint | Qaysi sahifa / Vazifasi | Izoh |
|---|---|---|---|
| **GET / POST** | `/finance/accounts/` | Hisoblar (Naqd kassa, Terminal, Bank) | Joriy balans va hisob turlari |
| **GET / PATCH / DELETE** | `/finance/accounts/{id}/` | Hisobni tahrirlash / o‘chirish | — |
| **GET / POST** | `/finance/categories/` | Moliya moddalari (Daromad / Xarajat) | `INCOME` / `EXPENSE` |
| **GET / POST** | `/finance/transactions/` | Tranzaksiyalar jurnali | Kirim va chiqim operatsiyalari |
| **GET / PATCH / DELETE** | `/finance/transactions/{id}/` | Tranzaksiyani tahrirlash / o‘chirish | Balansni avtomatik qayta hisoblaydi |
| **GET** | `/finance/monitoring/` | Moliya monitoringi & Balanslar | Umumiy tushum, xarajat va sof foyda |

---

## 🧪 Testlarni Ishga Tushirish

Loyihadagi barcha unit va integratsion testlarni ishga tushirish:
```bash
python manage.py test
```
