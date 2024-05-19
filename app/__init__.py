from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config


# Инициализация расширений
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'routes.login'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений с приложением
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    # Регистрация блюпринтов
    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app


# Импортируем модели после создания приложения и расширений
from app import models
