from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from apps.core.telegram import send_daily_summary_report
from apps.sozlamalar.models import Branch

class Command(BaseCommand):
    help = "Sends Bahor Cafe daily summary report to Telegram"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Report date in YYYY-MM-DD format (defaults to today)',
        )
        parser.add_argument(
            '--branch',
            type=int,
            help='Branch ID (optional)',
        )

    def handle(self, *args, **options):
        date_str = options.get('date')
        branch_id = options.get('branch')

        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid date format: {date_str}. Expected YYYY-MM-DD."))
                return

        branch = None
        if branch_id:
            branch = Branch.objects.filter(id=branch_id).first()
            if not branch:
                self.stderr.write(self.style.ERROR(f"Branch #{branch_id} not found."))
                return

        self.stdout.write(f"📊 Generating and sending daily report for {target_date or timezone.localdate()}...")

        ok, result = send_daily_summary_report(branch=branch, target_date=target_date, async_send=False)

        if ok:
            self.stdout.write(self.style.SUCCESS(f"✅ Daily report sent successfully!"))
            self.stdout.write(f"   Date: {result.get('date')}")
            self.stdout.write(f"   Revenue: {result.get('total_revenue')} UZS (Cash: {result.get('total_cash')}, Card: {result.get('total_card')})")
            self.stdout.write(f"   Paid Orders: {result.get('paid_count')}")
            self.stdout.write(f"   Cancelled Orders: {result.get('cancelled_count')}")
        else:
            self.stderr.write(self.style.WARNING(f"⚠️ Report sending skipped/failed: {result}"))
