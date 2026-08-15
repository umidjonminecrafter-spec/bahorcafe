import json
import logging
import threading
import urllib.request
import urllib.parse
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Count

logger = logging.getLogger('bahor_app')

def get_telegram_config(branch=None):
    """
    Retrieves Telegram Bot Token and Chat ID from database or environment/settings.
    """
    token = ""
    chat_id = ""
    notify_paid = True
    notify_cancelled = True
    notify_daily = True
    is_active = True

    try:
        from apps.sozlamalar.models import TelegramBotSettings
        qs = TelegramBotSettings.objects.all()
        if branch:
            obj = qs.filter(branch=branch).first() or qs.first()
        else:
            obj = qs.first()

        if obj:
            token = obj.bot_token.strip() if obj.bot_token else ""
            chat_id = obj.chat_id.strip() if obj.chat_id else ""
            is_active = obj.is_active
            notify_paid = obj.notify_order_paid
            notify_cancelled = obj.notify_order_cancelled
            notify_daily = obj.notify_daily_report
    except Exception as e:
        logger.warning(f"Error fetching TelegramBotSettings: {e}")

    # Fallback to settings or environment variables if not in DB
    if not token:
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''
    if not chat_id:
        chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '') or ''

    return {
        'token': token.strip(),
        'chat_id': chat_id.strip(),
        'is_active': is_active,
        'notify_paid': notify_paid,
        'notify_cancelled': notify_cancelled,
        'notify_daily': notify_daily
    }

def _send_http_request(token, chat_id, text, parse_mode='HTML'):
    """
    Synchronous worker that calls Telegram Bot API.
    """
    if not token or not chat_id:
        return False, "Token yoki Chat ID ko'rsatilmagan"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if res_data.get('ok'):
                return True, "Yuborildi"
            else:
                desc = res_data.get('description', 'Noma\'lum xatolik')
                logger.warning(f"Telegram API response error: {desc}")
                return False, desc
    except Exception as e:
        logger.warning(f"Telegram HTTP request error: {e}")
        return False, str(e)

def send_telegram_message(text, chat_id=None, bot_token=None, parse_mode='HTML', async_send=True):
    """
    Sends message to Telegram. Supports single or multiple comma-separated chat IDs.
    """
    config = get_telegram_config()
    token = bot_token or config['token']
    target_chat = chat_id or config['chat_id']

    if not token or not target_chat:
        logger.debug("Telegram notification skipped: No token or chat_id configured.")
        return False

    chat_ids = [c.strip() for c in str(target_chat).split(',') if c.strip()]

    def worker():
        for cid in chat_ids:
            try:
                _send_http_request(token, cid, text, parse_mode)
            except Exception as ex:
                logger.warning(f"Failed to send to Telegram chat {cid}: {ex}")

    if async_send:
        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()
        return True
    else:
        success = True
        for cid in chat_ids:
            ok, _ = _send_http_request(token, cid, text, parse_mode)
            if not ok:
                success = False
        return success

def format_uzs(amount):
    """Formats Decimal/Float amount into 100 000 UZS representation"""
    try:
        val = int(round(float(amount)))
        return f"{val:,}".replace(",", " ") + " UZS"
    except Exception:
        return f"{amount} UZS"

def send_order_paid_receipt(order):
    """
    Sends detailed paid order receipt to Telegram.
    """
    config = get_telegram_config(order.branch if hasattr(order, 'branch') else None)
    if not config['is_active'] or not config['notify_paid'] or not config['token'] or not config['chat_id']:
        return False

    # Header info
    branch_name = order.branch.name if (hasattr(order, 'branch') and order.branch) else "Bahor Cafe"
    
    if order.table:
        location = f"🍽 <b>Stol:</b> {order.table.name}"
    elif order.order_type == 'takeaway':
        location = "🛍 <b>Buyurtma turi:</b> Olib ketish (Takeaway)"
    elif order.order_type == 'delivery':
        location = "🚚 <b>Buyurtma turi:</b> Yetkazib berish (Delivery)"
    else:
        location = "📍 <b>Joylashuv:</b> Zal"

    waiter_name = order.assigned_waiter.name if order.assigned_waiter else "Kassa"
    pay_type_uz = "💵 Naqd pul" if order.payment_type == 'cash' else "💳 Karta / Terminal"
    if order.cash_amount > 0 and order.card_amount > 0:
        pay_type_uz = f"💵 Naqd: {format_uzs(order.cash_amount)} + 💳 Karta: {format_uzs(order.card_amount)}"

    paid_time = timezone.localtime(order.paid_at or timezone.now()).strftime("%d.%m.%Y %H:%M")

    # Dishes list
    items = order.items.all().select_related('product')
    items_text_list = []
    for idx, it in enumerate(items, 1):
        p_name = it.product_name_snapshot or (it.product.name if it.product else "Taom")
        qty_str = f"{it.qty:g}" if isinstance(it.qty, Decimal) else f"{float(it.qty):g}"
        price_str = format_uzs(it.unit_price)
        total_str = format_uzs(it.total_price)
        items_text_list.append(f"  {idx}. <b>{p_name}</b> x {qty_str} = {total_str}")

    items_block = "\n".join(items_text_list) if items_text_list else "  <i>Taomlar ko'rsatilmagan</i>"

    # Calculations
    subtotal_str = format_uzs(order.base_amount or 0)
    service_str = format_uzs(order.service_amount or 0)
    discount_str = format_uzs(order.discount_amount or 0)
    total_str = format_uzs(order.total_amount or 0)

    calc_lines = [f"💵 <b>Taomlar jami:</b> {subtotal_str}"]
    if order.discount_amount and order.discount_amount > 0:
        calc_lines.append(f"🎁 <b>Chegirma:</b> -{discount_str}")
    if order.service_amount and order.service_amount > 0:
        calc_lines.append(f"🏷 <b>Xizmat haqi ({order.service_percent}%):</b> +{service_str}")
    calc_block = "\n".join(calc_lines)

    msg = (
        f"🧾 <b>YANGI TO'LOV CHEKI — #{order.number or order.id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Filial:</b> {branch_name}\n"
        f"{location}\n"
        f"👤 <b>Xodim:</b> {waiter_name}\n"
        f"💳 <b>To'lov:</b> {pay_type_uz}\n"
        f"🕒 <b>Vaqt:</b> {paid_time}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>🍽 Buyurtma tarkibi:</b>\n"
        f"{items_block}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{calc_block}\n"
        f"💰 <b>JAMI TO'LANDI: {total_str}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>✨ Xaridingiz uchun rahmat!</i>"
    )

    return send_telegram_message(msg, async_send=True)

def send_order_cancelled_alert(order, reason=None, employee_name=None):
    """
    Sends alert to Telegram when an order is cancelled.
    """
    config = get_telegram_config(order.branch if hasattr(order, 'branch') else None)
    if not config['is_active'] or not config['notify_cancelled'] or not config['token'] or not config['chat_id']:
        return False

    branch_name = order.branch.name if (hasattr(order, 'branch') and order.branch) else "Bahor Cafe"
    location = f"Stol: {order.table.name}" if order.table else "Zal / Takeaway"
    waiter_name = order.assigned_waiter.name if order.assigned_waiter else "—"
    canceller = employee_name or "Admin / Kassir"
    cancel_reason = reason or "Mijoz rad etdi / Xatolik"
    total_str = format_uzs(order.total_amount or order.base_amount or 0)
    v_time = timezone.localtime(timezone.now()).strftime("%d.%m.%Y %H:%M")

    # Item preview
    items = order.items.all()[:5]
    items_summary = ", ".join([f"{it.product.name if it.product else 'Taom'} ({it.qty:g})" for it in items]) or "—"

    msg = (
        f"⚠️ <b>BUYURTMA BEKOR QILINDI — #{order.number or order.id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Filial:</b> {branch_name}\n"
        f"📍 <b>Joylashuv:</b> {location}\n"
        f"👤 <b>Ofitsiant:</b> {waiter_name}\n"
        f"❌ <b>Bekor qiluvchi:</b> {canceller}\n"
        f"📝 <b>Sabab:</b> {cancel_reason}\n"
        f"🍲 <b>Tarkib:</b> {items_summary}\n"
        f"💰 <b>Summa:</b> {total_str}\n"
        f"🕒 <b>Vaqt:</b> {v_time}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Iltimos, bekor qilish sababini nazorat qiling!</i>"
    )

    return send_telegram_message(msg, async_send=True)

def send_daily_summary_report(branch=None, target_date=None, async_send=False):
    """
    Generates and sends comprehensive daily summary report to Telegram.
    """
    from apps.order.models import Order, OrderItem
    
    report_date = target_date or timezone.localdate()
    branch_name = branch.name if branch else "Bahor Cafe"

    # Fetch orders for this date
    orders_qs = Order.objects.filter(created_at__date=report_date)
    if branch:
        orders_qs = orders_qs.filter(branch=branch)

    paid_orders = orders_qs.filter(status='paid')
    cancelled_orders = orders_qs.filter(status__in=['cancelled', 'canceled'])

    total_revenue = paid_orders.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0')
    total_cash = paid_orders.filter(payment_type='cash').aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0')
    total_card = paid_orders.filter(payment_type='card').aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0')
    
    paid_count = paid_orders.count()
    cancelled_count = cancelled_orders.count()
    cancelled_total = cancelled_orders.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0')
    avg_check = (total_revenue / paid_count) if paid_count > 0 else Decimal('0.0')

    # Top selling dishes
    top_items = (
        OrderItem.objects.filter(order__in=paid_orders)
        .values('product__name')
        .annotate(total_qty=Sum('qty'), total_sum=Sum('total_price'))
        .order_by('-total_qty')[:5]
    )

    top_list = []
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for i, it in enumerate(top_items):
        p_name = it['product__name'] or "Taom"
        q = it['total_qty'] or 0
        s = it['total_sum'] or 0
        medal = medals[i] if i < len(medals) else "🔹"
        top_list.append(f"{medal} <b>{p_name}</b> — {q:g} ta ({format_uzs(s)})")

    top_block = "\n".join(top_list) if top_list else "  <i>Sotuvlar mavjud emas</i>"

    date_str = report_date.strftime("%d-%B, %Y")

    msg = (
        f"📊 <b>KUNLIK HISOBOT — {branch_name}</b>\n"
        f"📅 <b>Sana:</b> {date_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>JAMI TUSHUM:</b> <b>{format_uzs(total_revenue)}</b>\n"
        f"  💵 <b>Naqd:</b> {format_uzs(total_cash)}\n"
        f"  💳 <b>Karta / Terminal:</b> {format_uzs(total_card)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 <b>To'langan cheklar:</b> {paid_count} ta\n"
        f"🎯 <b>O'rtacha chek:</b> {format_uzs(avg_check)}\n"
        f"❌ <b>Bekor qilinganlar:</b> {cancelled_count} ta ({format_uzs(cancelled_total)})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>🏆 Top 5 taomlar:</b>\n"
        f"{top_block}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Bahor Cafe Avtomatlashtirish Tizimi</i>"
    )

    config = get_telegram_config(branch)
    json_top_items = []
    for it in top_items:
        json_top_items.append({
            "product_name": it['product__name'] or "Taom",
            "total_qty": float(it['total_qty'] or 0),
            "total_sum": float(it['total_sum'] or 0)
        })

    stats_data = {
        "date": str(report_date),
        "total_revenue": float(total_revenue),
        "total_cash": float(total_cash),
        "total_card": float(total_card),
        "paid_count": paid_count,
        "cancelled_count": cancelled_count,
        "avg_check": float(avg_check),
        "top_items": json_top_items
    }

    if not config['is_active'] or not config['notify_daily'] or not config['token'] or not config['chat_id']:
        return False, stats_data

    ok = send_telegram_message(msg, async_send=async_send)
    return ok, stats_data

def test_telegram_connection(bot_token=None, chat_id=None):
    """
    Sends a test message to verify Telegram bot setup.
    """
    config = get_telegram_config()
    token = bot_token or config['token']
    target_chat = chat_id or config['chat_id']

    if not token:
        return False, "Bot Token kiritilmagan!"
    if not target_chat:
        return False, "Chat ID kiritilmagan!"

    now_str = timezone.localtime(timezone.now()).strftime("%d.%m.%Y %H:%M:%S")
    msg = (
        f"🤖 <b>Bahor Cafe Telegram Bot — Aloqa Testi</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Bot muvaffaqiyatli ulandi!\n"
        f"🕒 <b>Vaqt:</b> {now_str}\n"
        f"📌 <i>Endi barcha to'lov cheklari, bekor qilishlar va kunlik hisobotlar ushbu chatga yuboriladi.</i>"
    )

    return _send_http_request(token, target_chat, msg, parse_mode='HTML')

def send_telegram_reply(chat_id, text, reply_markup=None, bot_token=None):
    """
    Sends reply message with optional keyboard or inline markup.
    """
    config = get_telegram_config()
    token = bot_token or config['token']
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            return True
    except Exception as e:
        logger.warning(f"Error in send_telegram_reply: {e}")
        return False

def process_telegram_update(update):
    """
    Processes incoming webhook or long polling Telegram update.
    Identifies user phone, links admin, and responds to commands.
    """
    import re
    from apps.employee.models import Employee
    from apps.sozlamalar.models import TelegramBotSettings, Branch
    from apps.order.models import Order

    message = update.get('message') or update.get('edited_message')
    if not message:
        return {"ok": True, "status": "no_message"}

    chat = message.get('chat', {})
    chat_id = str(chat.get('id', ''))
    from_user = message.get('from', {})
    first_name = from_user.get('first_name', 'Foydalanuvchi')
    text = (message.get('text') or '').strip()
    contact = message.get('contact')

    if not chat_id:
        return {"ok": True, "status": "no_chat_id"}

    # 1. Contact shared via button
    if contact:
        raw_phone = contact.get('phone_number', '')
        clean_phone = re.sub(r'\D', '', raw_phone)
        last_9 = clean_phone[-9:] if len(clean_phone) >= 9 else clean_phone

        # Find employee in database
        emp = Employee.objects.filter(phone__endswith=last_9).first()
        
        # Link chat_id to TelegramBotSettings
        bot_settings = TelegramBotSettings.objects.first()
        if not bot_settings:
            bot_settings = TelegramBotSettings.objects.create(
                branch=Branch.objects.first(),
                chat_id=chat_id,
                is_active=True
            )
        else:
            existing_ids = [c.strip() for c in bot_settings.chat_id.split(',') if c.strip()]
            if chat_id not in existing_ids:
                existing_ids.append(chat_id)
                bot_settings.chat_id = ",".join(existing_ids)
            bot_settings.is_active = True
            bot_settings.save(update_fields=['chat_id', 'is_active', 'updated_at'])

        if emp:
            emp.telegram_chat_id = chat_id
            emp.save(update_fields=['telegram_chat_id', 'updated_at'])
            role_title = emp.role.name if emp.role else "Xodim"
            branch_title = emp.branch.name if emp.branch else "Bahor Cafe"

            welcome_msg = (
                f"✅ <b>Assalomu alaykum, {emp.name}!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>Foydalanuvchi:</b> {emp.name}\n"
                f"💼 <b>Lavozim:</b> {role_title}\n"
                f"📱 <b>Telefon:</b> +{clean_phone}\n"
                f"🏢 <b>Filial:</b> {branch_title}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 <b>Siz tizimga muvaffaqiyatli ulandingiz!</b>\n\n"
                f"📌 <b>Endi botingizga:</b>\n"
                f"• 🧾 Kassada to'langan har bir buyurtma cheki\n"
                f"• ⚠️ Bekor qilingan buyurtmalar\n"
                f"• 📊 Har kungi kunlik yakuniy hisobot\n"
                f"to'g'ridan-to'g'ri avtomatik kelib turadi.\n\n"
                f"<i>Buyruqlar:</i>\n"
                f"/hisobot — Bugungi hisobotni olish\n"
                f"/stats — Jonli kassa holati"
            )
        else:
            welcome_msg = (
                f"✅ <b>Assalomu alaykum, {first_name}!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📱 <b>Telefoningiz:</b> +{clean_phone}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🎉 <b>Siz Bahor Cafe tizimiga muvaffaqiyatli ulandingiz!</b>\n\n"
                f"📌 Barcha to'lov cheklari va kunlik hisobotlar ushbu botga keladi.\n\n"
                f"<i>Buyruqlar:</i>\n"
                f"/hisobot — Bugungi hisobotni olish\n"
                f"/stats — Jonli kassa holati"
            )

        send_telegram_reply(chat_id, welcome_msg, reply_markup={"remove_keyboard": True})
        return {"ok": True, "status": "authorized"}

    # 2. Text command /start
    if text.startswith('/start'):
        # Check if already registered
        emp = Employee.objects.filter(telegram_chat_id=chat_id).first()
        bot_settings = TelegramBotSettings.objects.first()
        is_registered = (emp is not None) or (bot_settings and chat_id in bot_settings.chat_id)

        if is_registered:
            name_label = emp.name if emp else first_name
            msg = (
                f"👋 <b>Assalomu alaykum, {name_label}!</b>\n\n"
                f"Siz avval tizimga ulangansiz. Barcha cheklar va hisobotlar ushbu chatga kelmoqda.\n\n"
                f"<i>Mavjud buyruqlar:</i>\n"
                f"/hisobot — Bugungi kunlik hisobotni olish\n"
                f"/stats — Jonli kassa statistikasi"
            )
            send_telegram_reply(chat_id, msg, reply_markup={"remove_keyboard": True})
        else:
            msg = (
                f"👋 <b>Assalomu alaykum, {first_name}!</b>\n"
                f"Bahor Cafe hisobot va kassa cheklari botiga xush kelibsiz.\n\n"
                f"🔐 <b>Tizim administratori ekanligingizni tasdiqlash uchun</b> quyidagi tugmani bosing va telefon raqamingizni yuboring:"
            )
            contact_keyboard = {
                "keyboard": [
                    [{"text": "📱 Telefon raqamni yuborish", "request_contact": True}]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": True
            }
            send_telegram_reply(chat_id, msg, reply_markup=contact_keyboard)

        return {"ok": True, "status": "start_processed"}

    # 3. /hisobot command
    if text.startswith('/hisobot') or text.lower() == 'hisobot':
        send_daily_summary_report(async_send=False)
        return {"ok": True, "status": "hisobot_sent"}

    # 4. /stats command
    if text.startswith('/stats') or text.lower() == 'statistika':
        today = timezone.localdate()
        today_orders = Order.objects.filter(created_at__date=today)
        paid_orders = today_orders.filter(status='paid')
        rev = paid_orders.aggregate(s=Sum('total_amount'))['s'] or Decimal('0.0')
        open_count = today_orders.filter(status__in=['open', 'sent_to_kitchen', 'ready']).count()
        paid_count = paid_orders.count()

        msg = (
            f"📈 <b>JONLI STATISTIKA — Bahor Cafe</b>\n"
            f"📅 <b>Sana:</b> {today.strftime('%d.%m.%Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Bugungi tushum:</b> <b>{format_uzs(rev)}</b>\n"
            f"🧾 <b>To'langan cheklar:</b> {paid_count} ta\n"
            f"🍽 <b>Hozir ochiq stollar:</b> {open_count} ta\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Batafsil kunlik hisobot: /hisobot</i>"
        )
        send_telegram_reply(chat_id, msg)
        return {"ok": True, "status": "stats_sent"}

    # Default fallback
    msg = (
        f"🤖 <b>Bahor Cafe Bot</b>\n\n"
        f"Mavjud buyruqlar:\n"
        f"/start — Qayta ishga tushirish\n"
        f"/hisobot — Bugungi hisobotni olish\n"
        f"/stats — Jonli kassa holati"
    )
    send_telegram_reply(chat_id, msg)
    return {"ok": True, "status": "default_reply"}

