from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EcoCart.settings')

app = Celery('EcoCart')

app.conf.beat_schedule = {
    'check-expiring-products': {
        'task': 'shopping.tasks.check_expiring_products',
        'schedule': crontab(minute=0, hour=0),  # 每天午夜执行
    },
}

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
