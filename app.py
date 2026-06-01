from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.customers import customers_bp
    from blueprints.deliveries import deliveries_bp
    from blueprints.invoices import invoices_bp
    from blueprints.payments import payments_bp
    from blueprints.reports import reports_bp
    from blueprints.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(customers_bp, url_prefix='/customers')
    app.register_blueprint(deliveries_bp, url_prefix='/deliveries')
    app.register_blueprint(invoices_bp, url_prefix='/invoices')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_bp, url_prefix='/api')

    return app
