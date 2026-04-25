import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user

from app import db, csrf
from app.models import Journey, TelegramConfig, User

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    journeys = Journey.query.filter_by(user_id=current_user.id).all()
    tg = TelegramConfig.query.filter_by(user_id=current_user.id).first()
    return render_template('index.html', journeys=journeys, telegram_config=tg)


@main_bp.route('/journey/add', methods=['GET', 'POST'])
@login_required
def add_journey():
    if request.method == 'POST':
        departure_id = request.form.get('departure_station_id', '')
        departure_name = request.form.get('departure_station_name', '')
        arrival_id = request.form.get('arrival_station_id', '')
        arrival_name = request.form.get('arrival_station_name', '')
        time_start = request.form.get('time_start', '')
        time_end = request.form.get('time_end', '')
        days = request.form.getlist('days')

        if not all([departure_id, arrival_id, time_start, time_end]):
            flash('Please fill all required fields.', 'error')
            return redirect(url_for('main.add_journey'))

        journey = Journey(
            user_id=current_user.id,
            departure_station_id=departure_id,
            departure_station_name=departure_name,
            arrival_station_id=arrival_id,
            arrival_station_name=arrival_name,
            time_start=time_start,
            time_end=time_end,
        )
        journey.set_days_list([int(d) for d in days] if days else list(range(7)))
        db.session.add(journey)
        db.session.commit()
        flash('Journey added!', 'success')
        return redirect(url_for('main.index'))

    return render_template('journey_form.html', journey=None)


@main_bp.route('/journey/<int:journey_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_journey(journey_id):
    journey = Journey.query.get_or_404(journey_id)
    if journey.user_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        journey.departure_station_id = request.form.get('departure_station_id', journey.departure_station_id)
        journey.departure_station_name = request.form.get('departure_station_name', journey.departure_station_name)
        journey.arrival_station_id = request.form.get('arrival_station_id', journey.arrival_station_id)
        journey.arrival_station_name = request.form.get('arrival_station_name', journey.arrival_station_name)
        journey.time_start = request.form.get('time_start', journey.time_start)
        journey.time_end = request.form.get('time_end', journey.time_end)
        days = request.form.getlist('days')
        journey.set_days_list([int(d) for d in days] if days else list(range(7)))
        db.session.commit()
        flash('Journey updated!', 'success')
        return redirect(url_for('main.index'))

    return render_template('journey_form.html', journey=journey)


@main_bp.route('/journey/<int:journey_id>/toggle', methods=['POST'])
@login_required
def toggle_journey(journey_id):
    journey = Journey.query.get_or_404(journey_id)
    if journey.user_id != current_user.id:
        return jsonify({'error': 'Forbidden'}), 403
    journey.active = not journey.active
    db.session.commit()
    return jsonify({'active': journey.active})


@main_bp.route('/journey/<int:journey_id>/delete', methods=['POST'])
@login_required
def delete_journey(journey_id):
    journey = Journey.query.get_or_404(journey_id)
    if journey.user_id != current_user.id:
        return jsonify({'error': 'Forbidden'}), 403
    db.session.delete(journey)
    db.session.commit()
    return jsonify({'success': True})


@main_bp.route('/api/stations')
def search_stations():
    """Proxy search to SNCF API - keeps API key server-side."""
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])

    from app.sncf import sncf_client
    stations = sncf_client.search_stations(q)
    return jsonify(stations)


@main_bp.route('/telegram/setup', methods=['GET', 'POST'])
@login_required
def telegram_setup():
    tg = TelegramConfig.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        bot_token = request.form.get('bot_token', '').strip()
        chat_id = request.form.get('chat_id', '').strip()

        if not bot_token:
            flash('Bot token required.', 'error')
            return redirect(url_for('main.telegram_setup'))

        if tg:
            tg.bot_token = bot_token
            if chat_id:
                tg.chat_id = chat_id
        else:
            tg = TelegramConfig(
                user_id=current_user.id,
                bot_token=bot_token,
                chat_id=chat_id,
            )
            db.session.add(tg)
        db.session.commit()

        # Test the bot
        from app.telegram_bot import test_bot
        verified, chat_id_result = test_bot(bot_token)
        if verified:
            tg.verified = True
            tg.chat_id = chat_id_result or tg.chat_id
            db.session.commit()
            flash('Telegram bot configured and verified!', 'success')
        else:
            flash('Bot token saved but verification failed. Make sure you started a conversation with your bot first.', 'warning')

        return redirect(url_for('main.index'))

    return render_template('telegram_setup.html', telegram_config=tg)


@main_bp.route('/telegram/generate-qr')
def telegram_qr():
    """Generate QR code linking to BotFather."""
    import qrcode
    import io
    import base64
    img = qrcode.make('https://t.me/BotFather')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    return jsonify({'qr': f'data:image/png;base64,{b64}'})


from flask import abort