from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from common.config import AppConfig

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=AppConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений с приложением
    db.init_app(app)
    migrate.init_app(app, db)

    return app
