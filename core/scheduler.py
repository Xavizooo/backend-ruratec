from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
from datetime import timedelta

def eliminar_publicaciones_expiradas():
    from .models import Publicacion
    limite = timezone.now() - timedelta(days=10)
    eliminadas = Publicacion.objects.filter(creado_en__lt=limite).delete()
    print(f"Publicaciones eliminadas: {eliminadas}")

def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    scheduler.add_job(
        eliminar_publicaciones_expiradas,
        "interval",
        hours=24,
        id="eliminar_publicaciones",
        replace_existing=True,
    )
    scheduler.start()
    print("Scheduler iniciado")