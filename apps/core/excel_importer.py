import io
import csv
import json
import re
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from django.utils import timezone

logger = logging.getLogger('bahor_app')

CANONICAL_FIELD_MAPPINGS = {
    'name': [
        'nomi', 'nom', 'mahsulot', 'tovar', 'tovar nomi', 'mahsulot nomi',
        'name', 'product_name', 'product', 'item', 'item_name', 'title',
        'наименование', 'название', 'товар', 'наименование товара', 'блюдо',
        'taom', 'taom nomi', 'taom_nomi', 'xomashyo', 'xomashyo nomi'
    ],
    'category': [
        'kategoriya', 'kategoriyasi', 'category', 'cat', 'guruh', 'guruhi',
        'категория', 'группа'
    ],
    'warehouse': [
        'ombor', 'omborxona', 'ombor nomi', 'warehouse', 'warehouse_name',
        'sklad', 'склад'
    ],
    'unit': [
        'birlik', 'birligi', 'unit', 'olchov', 'olchov birligi', 'o‘lchov birligi',
        "o'lchov", 'o‘lchov', 'ед', 'ед. изм.', 'ед.изм', 'единица', 'единица измерения'
    ],
    'barcode': [
        'shtrixkod', 'shtrix kod', 'shtrix-kod', 'barcode', 'bar code', 'bar_code',
        'штрихкод', 'штрих-код', 'штрих код', 'штрих'
    ],
    'mxik': [
        'mxik', 'mxik kodi', 'mxik_code', 'ikpu', 'ikpu_code', 'икпу',
        'код икпу', 'код мхик', 'мхик'
    ],
    'purchase_price': [
        'kelish narxi', 'kelish narx', 'kelish_narxi', 'tannarx', 'tan narxi',
        'kirim narxi', 'xarid narxi', 'purchase_price', 'cost_price', 'cost',
        'buy_price', 'цена прихода', 'приходная цена', 'себестоимость',
        'цена закупки', 'закупка'
    ],
    'selling_price': [
        'sotish narxi', 'sotish narx', 'sotish_narxi', 'sotuv narxi', 'narx',
        'narxi', 'price', 'selling_price', 'sale_price', 'retail_price',
        'цена', 'цена продажи', 'розничная цена', 'стоимость'
    ],
    'wholesale_price': [
        'ulgurji narxi', 'ulgurji narx', 'ulgurji_narxi', 'ulgurji',
        'wholesale_price', 'wholesale', 'optom narx', 'оптовая цена'
    ],
    'margin_percent': [
        'ustama', 'ustama foizi', 'ustama %', 'margin', 'margin_percent',
        'наценка'
    ],
    'qqs_rate': [
        'qqs', 'qqs stavkasi', 'qqs %', 'vat', 'vat_rate', 'ндс'
    ],
    'quantity': [
        'miqdor', 'miqdori', 'soni', 'son', 'qoldiq', 'mavjud', 'stock',
        'quantity', 'qty', 'count', 'amount', 'current_stock', 'количество',
        'остаток', 'кол-во', 'кол во', 'объем'
    ],
    'min_stock': [
        'min limit', 'min qoldiq', 'minimal limit', 'minimal qoldiq',
        'min_stock', 'мин. остаток', 'мин остаток', 'минимальный остаток'
    ],
    'max_stock': [
        'max limit', 'max qoldiq', 'maksimal limit', 'maksimal qoldiq',
        'max_stock', 'макс. остаток', 'макс остаток', 'максимальный остаток'
    ],
    'supplier': [
        'yetkazib beruvchi', 'yetkazuvchi', 'taminotchi', "ta'minotchi",
        'kontragent', 'supplier', 'vendor', 'поставщик', 'контрагент'
    ],
    'document_number': [
        'hujjat raqami', 'faktura raqami', 'faktura', 'invoys', 'document_number',
        'doc_num', 'invoice_number', 'номер документа', 'номер счета-фактуры',
        'номер накладной'
    ],
    'date': [
        'sana', 'vaqt', 'date', 'sana_vaqti', 'created_at', 'дата'
    ],
    'department': [
        'bolim', "bo'lim", "bo‘lim", 'oshxona bolimi', 'department',
        'отдел', 'кухня', 'цех'
    ],
    'notes': [
        'izoh', 'eslatma', 'note', 'notes', 'comment', 'примечание', 'комментарий'
    ]
}

def normalize_header(header: str) -> str:
    """Clean and normalize a header string for comparison."""
    if not header:
        return ""
    h = str(header).strip().lower()
    h = re.sub(r'[\s_\-]+', ' ', h)
    h = re.sub(r'[^\w\s%]', '', h)
    return h.strip()

def match_field_name(header: str) -> str:
    """Matches a table header to our canonical field names."""
    norm = normalize_header(header)
    if not norm:
        return ""

    for canonical, variations in CANONICAL_FIELD_MAPPINGS.items():
        if norm == canonical or norm in variations:
            return canonical
        for v in variations:
            if norm == normalize_header(v):
                return canonical
    return norm.replace(' ', '_')

def clean_decimal(val, default=Decimal('0.0')) -> Decimal:
    """Converts strings, floats, formatted prices into Decimal safely."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        try:
            return Decimal(str(val))
        except Exception:
            return default
    if isinstance(val, Decimal):
        return val

    s = str(val).strip()
    if not s:
        return default

    # Remove currency words/symbols
    s = re.sub(r'(?i)(so[\'‘`]?m|uzs|sum|\$|usd|rub|руб|\bkg\b|\bl\b|\bdona\b)', '', s).strip()
    # Handle thousand separators e.g. "1 500,50" or "1,500.50"
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            # European format: 1.500,50
            s = s.replace('.', '').replace(',', '.')
        else:
            # US format: 1,500.50
            s = s.replace(',', '')
    elif ',' in s:
        # Check if comma is decimal or thousand separator
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) <= 3:
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')

    s = s.replace(' ', '').replace('\xa0', '')
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default

def clean_string(val, default="") -> str:
    """Converts value to cleaned string."""
    if val is None:
        return default
    s = str(val).strip()
    return s

def clean_date(val, default=None):
    """Converts various date representations to a date object."""
    if val is None:
        return default or timezone.now().date()
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s:
        return default or timezone.now().date()

    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(s.split('T')[0] if 'T' in s else s, fmt).date()
        except ValueError:
            continue
    return default or timezone.now().date()

def parse_excel_file(file_obj) -> list:
    """Parses .xlsx / .xls using openpyxl or fallback."""
    import openpyxl

    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
    except Exception as e:
        logger.warning(f"Could not open Excel workbook: {e}")
        return []

    try:
        sheet = wb.active
        if not sheet:
            return []
        rows = list(sheet.iter_rows(values_only=True))
    except Exception as e:
        logger.warning(f"Error reading Excel sheet rows: {e}")
        return []

    if not rows:
        return []

    # Find the header row (first non-empty row)
    header_row_idx = 0
    header_cells = None
    for idx, r in enumerate(rows):
        if r and any(cell is not None and str(cell).strip() != '' for cell in r):
            header_row_idx = idx
            header_cells = [str(c).strip() if c is not None else f"col_{i}" for i, c in enumerate(r)]
            break

    if not header_cells:
        return []

    data_rows = []
    for r in rows[header_row_idx + 1:]:
        if not r or not any(cell is not None and str(cell).strip() != '' for cell in r):
            continue
        row_dict = {}
        for i, cell in enumerate(r):
            if i < len(header_cells):
                col_name = header_cells[i]
                row_dict[col_name] = cell
        data_rows.append(row_dict)

    return data_rows

def parse_csv_file(file_bytes: bytes) -> list:
    """Parses CSV with auto encoding and delimiter detection."""
    if not file_bytes or not file_bytes.strip():
        return []

    encodings = ['utf-8-sig', 'utf-8', 'windows-1251', 'cp1251', 'latin-1']
    text = None
    for enc in encodings:
        try:
            text = file_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        text = file_bytes.decode('utf-8', errors='ignore')

    # Detect delimiter
    sample = text[:4096]
    delimiters = [',', ';', '\t', '|']
    best_delim = ','
    max_count = 0
    for d in delimiters:
        cnt = sample.count(d)
        if cnt > max_count:
            max_count = cnt
            best_delim = d

    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=best_delim)
        return [row for row in reader if any(v and str(v).strip() for v in row.values())]
    except Exception as e:
        logger.warning(f"Error reading CSV: {e}")
        return []

def parse_xml_invoice(file_bytes: bytes) -> list:
    """Parses Soliq / Didik / E-faktura style XML file."""
    if not file_bytes or not file_bytes.strip():
        return []

    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(file_bytes)
    except Exception as e:
        logger.warning(f"Error parsing XML: {e}")
        return []

    rows = []
    # Look for common item elements (Product, Item, Row, Tovar, Tovarlar)
    item_nodes = root.findall('.//Product') or root.findall('.//Item') or root.findall('.//Tovar') or root.findall('.//Row') or root.findall('.//ProductList/Product')

    for node in item_nodes:
        row = {}
        for child in node:
            tag = child.tag.split('}')[-1] # strip XML namespace if any
            row[tag] = child.text
        # Also include attributes
        for attr, val in node.attrib.items():
            row[attr] = val
        if row:
            rows.append(row)

    return rows

def extract_rows_from_request(request) -> list:
    """
    Extracts structured raw rows from a Django REST Framework request.
    Supports:
    1. Uploaded files in request.FILES ('file', 'excel', 'document', 'import_file')
    2. JSON payload with list of items or dict containing 'items', 'products', 'rows', 'data'
    """
    # 1. Check for file upload
    file_obj = (
        request.FILES.get('file') or
        request.FILES.get('excel') or
        request.FILES.get('document') or
        request.FILES.get('import_file') or
        request.FILES.get('faktura')
    )

    if file_obj:
        fname = file_obj.name.lower()
        try:
            content = file_obj.read()
            file_obj.seek(0)
        except Exception:
            content = b""

        if not content or not content.strip():
            return []

        try:
            if fname.endswith(('.xlsx', '.xlsm', '.xltx')):
                return parse_excel_file(io.BytesIO(content))
            elif fname.endswith('.xls'):
                try:
                    return parse_excel_file(io.BytesIO(content))
                except Exception:
                    return parse_csv_file(content)
            elif fname.endswith(('.csv', '.txt', '.tsv')):
                return parse_csv_file(content)
            elif fname.endswith('.xml'):
                return parse_xml_invoice(content)
            elif fname.endswith('.json'):
                parsed = json.loads(content.decode('utf-8', errors='ignore'))
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    return parsed.get('items') or parsed.get('products') or parsed.get('rows') or parsed.get('data') or [parsed]
            else:
                # Try Excel first, then CSV
                parsed_res = parse_excel_file(io.BytesIO(content))
                if parsed_res:
                    return parsed_res
                return parse_csv_file(content)
        except Exception as e:
            logger.warning(f"Error parsing uploaded file {fname}: {e}")
            return []

    # 2. Check JSON or multipart data
    data = request.data
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('items', 'products', 'rows', 'data', 'tovarlar', 'mahsulotlar'):
            if key in data and isinstance(data[key], list):
                return data[key]
        if 'file_content' in data:
            import base64
            try:
                decoded = base64.b64decode(data['file_content'])
                return parse_excel_file(io.BytesIO(decoded))
            except Exception:
                pass

    return []

def normalize_row_dict(raw_dict: dict) -> dict:
    """Converts raw headers into normalized field keys with typed values."""
    norm_dict = {}
    for key, val in raw_dict.items():
        field = match_field_name(str(key))
        if field:
            norm_dict[field] = val

    return {
        'name': clean_string(norm_dict.get('name') or raw_dict.get('name') or raw_dict.get('nomi') or raw_dict.get('product_name')),
        'category': clean_string(norm_dict.get('category') or raw_dict.get('category') or raw_dict.get('kategoriya')),
        'warehouse': clean_string(norm_dict.get('warehouse') or raw_dict.get('warehouse') or raw_dict.get('ombor')),
        'unit': clean_string(norm_dict.get('unit') or raw_dict.get('unit') or raw_dict.get('birlik') or 'kg'),
        'barcode': clean_string(norm_dict.get('barcode') or raw_dict.get('barcode') or raw_dict.get('shtrixkod')),
        'mxik': clean_string(norm_dict.get('mxik') or raw_dict.get('mxik') or raw_dict.get('ikpu')),
        'purchase_price': clean_decimal(norm_dict.get('purchase_price') or raw_dict.get('purchase_price') or raw_dict.get('cost_price') or raw_dict.get('kelish_narxi') or raw_dict.get('tannarx')),
        'selling_price': clean_decimal(norm_dict.get('selling_price') or raw_dict.get('selling_price') or raw_dict.get('price') or raw_dict.get('narx') or raw_dict.get('sotish_narxi')),
        'wholesale_price': clean_decimal(norm_dict.get('wholesale_price') or raw_dict.get('wholesale_price') or raw_dict.get('ulgurji_narxi')),
        'margin_percent': clean_decimal(norm_dict.get('margin_percent') or raw_dict.get('margin_percent') or raw_dict.get('margin') or raw_dict.get('ustama')),
        'qqs_rate': clean_decimal(norm_dict.get('qqs_rate') or raw_dict.get('qqs_rate') or raw_dict.get('qqs')),
        'quantity': clean_decimal(norm_dict.get('quantity') or raw_dict.get('quantity') or raw_dict.get('qty') or raw_dict.get('miqdor') or raw_dict.get('soni') or raw_dict.get('current_stock')),
        'min_stock': clean_decimal(norm_dict.get('min_stock') or raw_dict.get('min_stock') or raw_dict.get('min_limit')),
        'max_stock': clean_decimal(norm_dict.get('max_stock') or raw_dict.get('max_stock') or raw_dict.get('max_limit')),
        'supplier': clean_string(norm_dict.get('supplier') or raw_dict.get('supplier') or raw_dict.get('yetkazib_beruvchi')),
        'document_number': clean_string(norm_dict.get('document_number') or raw_dict.get('document_number') or raw_dict.get('faktura_raqami')),
        'department': clean_string(norm_dict.get('department') or raw_dict.get('department') or raw_dict.get('bolim') or raw_dict.get('bo\'lim')),
        'notes': clean_string(norm_dict.get('notes') or raw_dict.get('notes') or raw_dict.get('izoh')),
        'date': clean_date(norm_dict.get('date') or raw_dict.get('date') or raw_dict.get('sana')),
        'raw': raw_dict
    }
