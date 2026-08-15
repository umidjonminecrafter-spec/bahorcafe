from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        try:
            from apps.core.telegram import start_daily_report_scheduler
            start_daily_report_scheduler()
        except Exception:
            pass

