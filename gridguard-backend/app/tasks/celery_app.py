"""
GridGuard AI — Celery Application & Beat Schedule
"""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "gridguard",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.weather",
        "app.tasks.aqi",
        "app.tasks.traffic",
        "app.tasks.policy_tasks",
        "app.tasks.payout_tasks",
        "app.tasks.maintenance",
    ],
)

# ── Celery Configuration ──
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=4,
    result_expires=3600,
    task_soft_time_limit=300,  # 5 min soft limit
    task_time_limit=600,       # 10 min hard limit
)

# ── Beat Schedule (Periodic Tasks) ──
celery_app.conf.beat_schedule = {
    # Task 1: Poll weather events every 15 minutes
    "poll-weather-events": {
        "task": "app.tasks.weather.poll_weather_events",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "polling"},
    },

    # Task 2: Poll AQI events every 30 minutes
    "poll-aqi-events": {
        "task": "app.tasks.aqi.poll_aqi_events",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "polling"},
    },

    # Task 3: Poll traffic events every 15 minutes
    "poll-traffic-events": {
        "task": "app.tasks.traffic.poll_traffic_events",
        "schedule": crontab(minute="*/15"),
        "options": {"queue": "polling"},
    },

    # Task 4: Generate weekly policies — Sunday 22:00 IST (16:30 UTC)
    "generate-weekly-policies": {
        "task": "app.tasks.policy_tasks.generate_weekly_policies",
        "schedule": crontab(hour=16, minute=30, day_of_week=0),  # Sunday UTC
        "options": {"queue": "policies"},
    },

    # Task 5: Deduct weekly premiums — Monday 06:00 IST (00:30 UTC)
    "deduct-weekly-premiums": {
        "task": "app.tasks.policy_tasks.deduct_weekly_premiums",
        "schedule": crontab(hour=0, minute=30, day_of_week=1),  # Monday UTC
        "options": {"queue": "policies"},
    },

    # Task 7: Resolve stale events — every 2 hours
    "resolve-stale-events": {
        "task": "app.tasks.maintenance.resolve_stale_events",
        "schedule": crontab(minute=0, hour="*/2"),
        "options": {"queue": "maintenance"},
    },
}
