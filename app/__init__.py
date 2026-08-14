from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access Syldesk."
login_manager.login_message_category = "info"


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    login_manager.init_app(app)

    from app.auth import auth as auth_bp
    from app.dashboard import dashboard as dashboard_bp
    from app.opportunities import opportunities as opportunities_bp
    from app.inspiration import inspiration as inspiration_bp
    from app.profiles import profiles as profiles_bp
    from app.skills import skills as skills_bp
    from app.applications import applications as applications_bp
    from app.library import library as library_bp
    from app.backup import backup as backup_bp
    from app.projects import projects as projects_bp
    from app.notifications import notifications as notifications_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(opportunities_bp, url_prefix="/opportunities")
    app.register_blueprint(inspiration_bp, url_prefix="/inspiration")
    app.register_blueprint(profiles_bp, url_prefix="/profiles")
    app.register_blueprint(skills_bp, url_prefix="/skills")
    app.register_blueprint(applications_bp, url_prefix="/applications")
    app.register_blueprint(library_bp, url_prefix="/library")
    app.register_blueprint(backup_bp, url_prefix="/backup")
    app.register_blueprint(projects_bp, url_prefix="/projects")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    from app.main import main as main_bp
    app.register_blueprint(main_bp)

    return app
