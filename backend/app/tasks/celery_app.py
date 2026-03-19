"""
GridGuard AI — Celery App Configuration
"""

from celery import Celery
from celery.schedules import crontab

# Import settings lazily to avoid circular deps at module level
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "gridguard",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

app.conf.timezone = "Asia/Kolkata"
app.conf.enable_utc = True
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]

# Auto-discover tasks
app.autodiscover_tasks([
    "app.tasks.weather_poller",
    "app.tasks.aqi_poller",
    "app.tasks.traffic_poller",
    "app.tasks.policy_generator",
    "app.tasks.premium_deductor",
    "app.tasks.payout_eligibility",
    "app.tasks.event_resolver",
    "app.tasks.health_broadcaster",
])

# Beat schedule
app.conf.beat_schedule = {
    "poll-weather-events": {
        "task": "app.tasks.weather_poller.poll_weather_events",
        "schedule": crontab(minute="*/15"),
    },
    "poll-aqi-events": {
        "task": "app.tasks.aqi_poller.poll_aqi_events",
        "schedule": crontab(minute="*/30"),
    },
    "poll-traffic-events": {
        "task": "app.tasks.traffic_poller.poll_traffic_events",
        "schedule": crontab(minute="*/15"),
    },
    "generate-weekly-policies": {
        "task": "app.tasks.policy_generator.generate_weekly_policies",
        "schedule": crontab(hour=16, minute=30, day_of_week=0),  # Sun 22:00 IST = 16:30 UTC
    },
    "deduct-weekly-premiums": {
        "task": "app.tasks.premium_deductor.deduct_weekly_premiums",
        "schedule": crontab(hour=0, minute=30, day_of_week=1),  # Mon 06:00 IST = 00:30 UTC
    },
    "resolve-stale-events": {
        "task": "app.tasks.event_resolver.resolve_stale_events",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    "system-health-broadcast": {
        "task": "app.tasks.health_broadcaster.system_health_broadcast",
        "schedule": 60.0,  # every 60 seconds
    },
}
