import os
import logging
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from authlib.integrations.flask_client import OAuth

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('chouchou')

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
oauth = OAuth()

def create_app():
    app = Flask(__name__)

    # Config
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    # Use absolute path for SQLite to avoid issues with working directory
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, 'chouchou.db')
        db_url = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['APPLICATION_ROOT'] = os.environ.get('APPLICATION_ROOT', '/chouchoualerte')
    app.config['SNCF_API_TOKEN'] = os.environ.get('SNCF_API_TOKEN', '')
    app.config['DISRUPTION_CHECK_INTERVAL'] = int(os.environ.get('DISRUPTION_CHECK_INTERVAL', '300'))

    # OAuth config
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID', '')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    app.config['GOOGLE_DISCOVERY_URL'] = 'https://accounts.google.com/.well-known/openid-configuration'
    app.config['GITHUB_CLIENT_ID'] = os.environ.get('GITHUB_CLIENT_ID', '')
    app.config['GITHUB_CLIENT_SECRET'] = os.environ.get('GITHUB_CLIENT_SECRET', '')

    # ProxyFix for subpath deployment behind Caddy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'

    # OAuth setup
    oauth.init_app(app)
    if app.config['GOOGLE_CLIENT_ID']:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
            client_kwargs={'scope': 'openid email profile'},
        )
    if app.config['GITHUB_CLIENT_ID']:
        oauth.register(
            name='github',
            client_id=app.config['GITHUB_CLIENT_ID'],
            client_secret=app.config['GITHUB_CLIENT_SECRET'],
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )

    @app.before_request
    def log_request():
        log.info('REQUEST %s %s | X-Forwarded-Prefix=%s X-Forwarded-Proto=%s | root_path=%s APPLICATION_ROOT=%s',
                 request.method, request.path,
                 request.headers.get('X-Forwarded-Prefix', ''),
                 request.headers.get('X-Forwarded-Proto', ''),
                 request.root_path,
                 app.config.get('APPLICATION_ROOT', ''))

    @app.after_request
    def log_response(response):
        log.info('RESPONSE %s %s -> %s | Location=%s',
                 request.method, request.path, response.status_code,
                 response.headers.get('Location', ''))
        return response

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, int(user_id))

    # Register blueprints
    from app.auth import auth_bp
    from app.routes import main_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Create tables / migrate schema
    with app.app_context():
        from app.models import User, Journey, TelegramConfig
        db.create_all()

        # Migrate: add user_id column to journeys if missing (older DBs)
        import sqlite3
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if db_path and os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cols = [row[1] for row in conn.execute('PRAGMA table_info(journeys)').fetchall()]
            if 'user_id' not in cols:
                log.warning('Migrating journeys table: adding user_id column')
                conn.execute('ALTER TABLE journeys ADD COLUMN user_id INTEGER REFERENCES users(id)')
                conn.commit()
            # Same for telegram_configs
            cols = [row[1] for row in conn.execute('PRAGMA table_info(telegram_configs)').fetchall()]
            if 'user_id' not in cols:
                log.warning('Migrating telegram_configs table: adding user_id column')
                conn.execute('ALTER TABLE telegram_configs ADD COLUMN user_id INTEGER REFERENCES users(id)')
                conn.commit()
            if 'verified' not in cols:
                log.warning('Migrating telegram_configs table: adding verified column')
                conn.execute('ALTER TABLE telegram_configs ADD COLUMN verified BOOLEAN DEFAULT 0')
                conn.commit()
            conn.close()

    # Start disruption checker
    from app.disruption_checker import start_checker
    start_checker(app)

    return app