import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "syldesk-dev-secret-key-change-in-prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'syldesk.db'}"


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'syldesk.db'}"
    )
    # If DATABASE_URL starts with postgres://, SQLAlchemy requires postgresql://
    @classmethod
    def init_app(cls, app):
        uri = cls.SQLALCHEMY_DATABASE_URI
        if uri and uri.startswith("postgres://"):
            cls.SQLALCHEMY_DATABASE_URI = uri.replace("postgres://", "postgresql://", 1)


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
