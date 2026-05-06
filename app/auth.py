import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, session, current_app
from flask_login import login_user, logout_user, current_user

from app import db, oauth, csrf
from app.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return render_template('login.html',
                           google_enabled=bool(current_app.config.get('GOOGLE_CLIENT_ID')),
                           github_enabled=bool(current_app.config.get('GITHUB_CLIENT_ID')))


@auth_bp.route('/login/google')
def login_google():
    if not oauth.has_provider('google'):
        flash('Google login not configured.', 'error')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/login/google/callback')
@csrf.exempt
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash('Google login failed.', 'error')
        return redirect(url_for('auth.login'))

    userinfo = token.get('userinfo')
    if not userinfo:
        userinfo = oauth.google.userinfo()

    google_id = userinfo.get('sub') or userinfo.get('id')
    user = User.query.filter_by(google_id=google_id).first()
    if user:
        user.email = userinfo.get('email', '')
        user.name = userinfo.get('name', '')
        user.picture = userinfo.get('picture', '')
    else:
        user = User(
            google_id=google_id,
            email=userinfo.get('email', ''),
            name=userinfo.get('name', ''),
            picture=userinfo.get('picture', ''),
        )
        db.session.add(user)
    db.session.commit()
    login_user(user)

    # Migrate guest data if exists
    _migrate_guest_data(user)

    return redirect(url_for('main.index'))


@auth_bp.route('/login/github')
def login_github():
    if not oauth.has_provider('github'):
        flash('GitHub login not configured.', 'error')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.github_callback', _external=True)
    return oauth.github.authorize_redirect(redirect_uri)


@auth_bp.route('/login/github/callback')
@csrf.exempt
def github_callback():
    try:
        token = oauth.github.authorize_access_token()
    except Exception:
        flash('GitHub login failed.', 'error')
        return redirect(url_for('auth.login'))

    resp = oauth.github.get('user', token=token)
    profile = resp.json()

    github_id = str(profile.get('id'))
    user = User.query.filter_by(github_id=github_id).first()

    email = profile.get('email', '') or ''
    name = profile.get('name', '') or profile.get('login', '')
    picture = profile.get('avatar_url', '')

    if user:
        user.email = email
        user.name = name
        user.picture = picture
    else:
        user = User(
            github_id=github_id,
            email=email,
            name=name,
            picture=picture,
        )
        db.session.add(user)
    db.session.commit()
    login_user(user)

    _migrate_guest_data(user)

    return redirect(url_for('main.index'))


@auth_bp.route('/login/guest')
def login_guest():
    guest_session_id = str(uuid.uuid4())
    user = User(
        guest_session_id=guest_session_id,
        is_guest=True,
        name='Guest',
    )
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for('main.index'))


@auth_bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('auth.login'))


def _migrate_guest_data(user):
    """Migrate data from guest session to authenticated user."""
    guest_id = session.get('guest_user_id')
    if not guest_id:
        return
    guest = User.query.get(guest_id)
    if not guest or not guest.is_guest:
        return

    # Move journeys
    from app.models import Journey, TelegramConfig
    Journey.query.filter_by(user_id=guest.id).update({'user_id': user.id})

    # Move telegram config
    tg = TelegramConfig.query.filter_by(user_id=guest.id).first()
    if tg:
        existing = TelegramConfig.query.filter_by(user_id=user.id).first()
        if existing:
            db.session.delete(existing)
        tg.user_id = user.id

    # Delete guest user
    db.session.delete(guest)
    db.session.commit()
    session.pop('guest_user_id', None)