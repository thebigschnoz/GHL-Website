from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from poll_api import fetch_and_process_games_task

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GHLWebsiteDjango.settings')

app = Celery('GHLWebsiteDjango', broker='redis://localhost:6380/0')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks in Django apps.
app.autodiscover_tasks()

@app.task(bind=True)
def run_poll_api(self):
    fetch_and_process_games_task()
    pass

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    pass