from __future__ import absolute_import, unicode_literals
from GHLWebsiteDjango.poll_api import fetch_and_process_games_task
from GHLWebsiteDjango.celery import app as celery_app

__all__ = ('celery_app',)