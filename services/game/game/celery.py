from __future__ import absolute_import, unicode_literals
import os
from celery import Celery


# Establece el módulo de configuración de Django como predeterminado
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'game.settings')

# Inicializa Celery
app = Celery('game')

# Carga la configuración de Django en Celery
app.config_from_object('django.conf:settings', namespace='CELERY')



# # Enrutar tareas a la cola 'shared_queue'
# app.conf.task_routes = {
#     'game.tasks.shared_task': {'queue': 'shared_queue', 'routing_key': 'task.shared'},
# }

# Descubre automáticamente las tareas en las apps instaladas
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
