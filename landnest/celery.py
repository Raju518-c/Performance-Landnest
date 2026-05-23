import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'landnest.settings')

app = Celery('landnest')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'check-expired-subscriptions': {
        'task': 'users.tasks.check_expired_subscriptions',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
    'cache-city-properties': {
        'task': 'property.tasks.cache_city_properties',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes
    },
}

app.conf.timezone = 'Asia/Kolkata'
