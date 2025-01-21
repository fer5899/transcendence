from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Establece el módulo de configuración de Django como predeterminado
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tournaments_project.settings')

# Inicializa Celery
app = Celery('tournaments_project')

# Carga la configuración de Django en Celery
app.config_from_object('django.conf:settings', namespace='CELERY')




# Descubre automáticamente las tareas en las apps instaladas
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
