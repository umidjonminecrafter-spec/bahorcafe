import time
import json
import logging
import urllib.request
from django.core.management.base import BaseCommand
from apps.core.telegram import get_telegram_config, process_telegram_update

logger = logging.getLogger('bahor_app')

class Command(BaseCommand):
    help = "Runs Telegram Bot polling listener to handle /start, phone verification, and commands"

    def handle(self, *args, **options):
        config = get_telegram_config()
        token = config.get('token')

        if not token:
            self.stderr.write(self.style.ERROR("❌ TELEGRAM_BOT_TOKEN topilmadi. Sozlamalardan bot tokenni kiriting."))
            return

        self.stdout.write(self.style.SUCCESS(f"🚀 Telegram Bot polling ishga tushdi (Token: {token[:12]}...)"))
        self.stdout.write("Kutilmoqda... (To'xtatish uchun Ctrl+C)")

        offset = 0
        while True:
            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=20"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=25) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    if data.get('ok'):
                        updates = data.get('result', [])
                        for u in updates:
                            u_id = u.get('update_id')
                            offset = max(offset, u_id + 1)
                            self.stdout.write(f"📩 Yangi xabar olindi: update_id={u_id}")
                            res = process_telegram_update(u)
                            self.stdout.write(f"   Natija: {res.get('status')}")
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("\n🛑 Bot to'xtatildi."))
                break
            except Exception as e:
                logger.warning(f"Polling error: {e}")
                time.sleep(2)
