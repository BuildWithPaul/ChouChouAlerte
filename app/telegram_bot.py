import requests
from flask import current_app


def send_telegram_message(bot_token, chat_id, text):
    """Send a message via Telegram Bot API."""
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def test_bot(bot_token):
    """Test if a bot token is valid and get chat ID from recent updates."""
    try:
        # Verify token works
        resp = requests.get(
            f'https://api.telegram.org/bot{bot_token}/getMe',
            timeout=10,
        )
        if resp.status_code != 200:
            return False, None

        # Try to get updates to find chat_id
        resp = requests.get(
            f'https://api.telegram.org/bot{bot_token}/getUpdates',
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            updates = data.get('result', [])
            if updates:
                # Get chat_id from most recent message
                last = updates[-1]
                chat_id = str(last.get('message', {}).get('chat', {}).get('id', ''))
                return True, chat_id

        return True, None
    except Exception:
        return False, None


def get_bot_info(bot_token):
    """Get bot username/info."""
    try:
        resp = requests.get(
            f'https://api.telegram.org/bot{bot_token}/getMe',
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get('result', {})
        return None
    except Exception:
        return None


def format_disruption_message(journey, disruptions):
    """Format a disruption notification message."""
    dep = journey.departure_station_name
    arr = journey.arrival_station_name
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    active_days = ', '.join(days[d] for d in journey.get_days_list())
    time_slot = f"{journey.time_start}-{journey.time_end}"

    msg = f"🚨 <b>Disruption Alert</b>\n\n"
    msg += f"📍 <b>Journey:</b> {dep} → {arr}\n"
    msg += f"🕐 <b>Time slot:</b> {time_slot}\n"
    msg += f"📅 <b>Days:</b> {active_days}\n\n"

    if disruptions:
        msg += f"⚠️ <b>{len(disruptions)} disruption(s) detected:</b>\n"
        for d in disruptions[:5]:
            msg += f"• {d}\n"
    else:
        msg += "✅ Checked for disruptions on your route."

    return msg