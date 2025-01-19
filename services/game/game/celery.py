from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from kombu import Queue  # Importar Queue desde Kombu para configurar las colas

# Establece el módulo de configuración de Django como predeterminado
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'game.settings')

# Inicializa Celery
app = Celery('game')

# Carga la configuración de Django en Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configuración de colas: crea la cola 'create_game'
app.conf.task_queues = (
    Queue('create_game', routing_key='task.create_game'),  # Cola personalizada
)

# Enrutar tareas a la cola 'create_game'
app.conf.task_routes = {
    'game.tasks.create_game_task': {'queue': 'create_game', 'routing_key': 'task.create_game'},
}

# Descubre automáticamente las tareas en las apps instaladas
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
