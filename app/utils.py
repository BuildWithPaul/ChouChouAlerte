from app import db
from app.models import User, Journey, TelegramConfig


def get_or_create_guest(user_id):
    """Used by session-based guest users."""
    user = db.session.get(User, user_id)
    if not user:
        user = User(is_guest=True, name='Guest')
        db.session.add(user)
        db.session.commit()
    return user