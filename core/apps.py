from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

from django.apps import AppConfig

from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            try:
                from .scheduler import iniciar_scheduler
                iniciar_scheduler()
            except Exception as e:
                print(f"Scheduler no iniciado: {e}")