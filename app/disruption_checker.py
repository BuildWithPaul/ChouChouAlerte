import threading
from datetime import datetime
from flask import current_app
from apscheduler.schedulers.background import BackgroundScheduler

from app import db
from app.models import Journey, TelegramConfig, User

scheduler = BackgroundScheduler()
scheduler_lock = threading.Lock()


def check_disruptions_for_journey(app, journey):
    """Check disruptions for a single journey and notify via Telegram if found."""
    with app.app_context():
        from app.sncf import sncf_client

        # Check if journey is still active and today is a monitored day
        j = db.session.get(Journey, journey.id)
        if not j or not j.active:
            return

        now = datetime.now()
        # Monday=0 in Python, matches our scheme
        day_of_week = now.weekday()
        if day_of_week not in j.get_days_list():
            return

        # Check if current time is within the monitored time window
        current_time = now.strftime('%H:%M')
        if not (j.time_start <= current_time <= j.time_end):
            return

        # Get disruptions
        disruptions = sncf_client.get_traffic_info(
            j.departure_station_id,
            j.arrival_station_id,
        )

        if not disruptions:
            return

        # Format and send notification
        tg = TelegramConfig.query.filter_by(user_id=j.user_id, verified=True).first()
        if not tg or not tg.bot_token or not tg.chat_id:
            return

        from app.telegram_bot import send_telegram_message, format_disruption_message
        msg = format_disruption_message(j, disruptions)
        send_telegram_message(tg.bot_token, tg.chat_id, msg)


def check_all_disruptions(app):
    """Periodic check for all active journeys."""
    with app.app_context():
        journeys = Journey.query.filter_by(active=True).all()
        for journey in journeys:
            check_disruptions_for_journey(app, journey)


def start_checker(app):
    """Start the background scheduler for disruption checks."""
    interval = app.config.get('DISRUPTION_CHECK_INTERVAL', 300)

    # Only start scheduler once
    if not scheduler.running:
        scheduler.add_job(
            check_all_disruptions,
            'interval',
            seconds=interval,
            id='disruption_check',
            args=[app],
            replace_existing=True,
        )
        try:
            scheduler.start()
        except Exception:
            pass