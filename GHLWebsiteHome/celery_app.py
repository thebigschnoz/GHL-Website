from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GHLWebsiteHome.GHLWebsiteDjango.settings')

app = Celery('GHLWebsiteDjango', broker='redis://localhost:6379/0', include=['GHLWebsiteDjango.poll_api'])
app.conf.enable_utc = False
app.autodiscover_tasks()