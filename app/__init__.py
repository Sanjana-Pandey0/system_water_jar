from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
from datetime import datetime, timedelta

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.customers import customers_bp
    from app.blueprints.deliveries import deliveries_bp
    from app.blueprints.billing import billing_bp
    from app.blueprints.payments import payments_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(deliveries_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    # Context processors
    @app.context_processor
    def inject_globals():
        return {'now': datetime.utcnow(), 'timedelta': timedelta}

    @app.template_filter('currency')
    def currency_filter(value):
        try:
            return f'₹{float(value):,.2f}'
        except:
            return value

    with app.app_context():
        db.create_all()
        _seed_defaults()

    return app


def _seed_defaults():
    from app.models.user import User
    from app.models.settings import Settings

    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@aquaflow.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    defaults = {
        'business_name': 'AquaFlow Water Supply',
        'business_address': '123 Water Lane, Industrial Area',
        'business_city': 'Mumbai',
        'business_state': 'Maharashtra',
        'business_pin': '400001',
        'business_mobile': '+91 98765 43210',
        'business_email': 'info@aquaflow.com',
        'business_gst': '27AABCU9603R1ZX',
        'default_jar_rate': '30',
        'jar_warning_threshold': '10',
        'gst_percent': '0',
    }
    for k, v in defaults.items():
        if not Settings.query.filter_by(key=k).first():
            db.session.add(Settings(key=k, value=v))
    db.session.commit()
