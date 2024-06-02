from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from tinkoff.invest import Quotation, MoneyValue
from app.config import AppConfig

db = SQLAlchemy()
migrate = Migrate()


# todo а эти 2 поедут в helper
# Функция для преобразования Quotation в float
def q2f(quotation: Quotation | MoneyValue, digits=2):
    return round(quotation.units + quotation.nano * 1e-9, digits)


# Функция для преобразования float в Quotation
def f2q(value):
    units = int(value)
    nano = int(round(value - units, 2) * 1e9)
    return Quotation(units=units, nano=nano)


def create_app(config_class=AppConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Инициализация расширений с приложением
    db.init_app(app)
    migrate.init_app(app, db)

    return app
