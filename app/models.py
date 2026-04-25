from datetime import datetime
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(120), unique=True, nullable=True)
    github_id = db.Column(db.String(120), unique=True, nullable=True)
    guest_session_id = db.Column(db.String(200), unique=True, nullable=True)
    email = db.Column(db.String(200), default='')
    name = db.Column(db.String(200), default='')
    picture = db.Column(db.String(500), default='')
    is_guest = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    journeys = db.relationship('Journey', backref='user', lazy=True)
    telegram_config = db.relationship('TelegramConfig', backref='user', uselist=False)


class Journey(db.Model):
    __tablename__ = 'journeys'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    departure_station_id = db.Column(db.String(50), nullable=False)
    departure_station_name = db.Column(db.String(200), nullable=False)
    arrival_station_id = db.Column(db.String(50), nullable=False)
    arrival_station_name = db.Column(db.String(200), nullable=False)
    time_start = db.Column(db.String(5), nullable=False)  # HH:MM format
    time_end = db.Column(db.String(5), nullable=False)    # HH:MM format
    days_of_week = db.Column(db.String(50), default='0,1,2,3,4,5,6')  # 0=Mon..6=Sun
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_days_list(self):
        if not self.days_of_week:
            return []
        return [int(d) for d in self.days_of_week.split(',')]

    def set_days_list(self, days):
        self.days_of_week = ','.join(str(d) for d in sorted(days))


class TelegramConfig(db.Model):
    __tablename__ = 'telegram_configs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    bot_token = db.Column(db.String(200), default='')
    chat_id = db.Column(db.String(100), default='')
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)