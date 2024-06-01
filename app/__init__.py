from datetime import datetime, timedelta

from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from app.config import AppConfig

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'common.login'


def create_app(config_class=AppConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['FLASK_ADMIN_SWATCH'] = 'cosmo' if AppConfig.DEBUG_MODE else 'cerulean'

    # Инициализация расширений с приложением
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    # Проверка авторизации перед каждым запросом,
    # а определение @login.user_loader лежит в моделях
    @app.before_request
    def require_login():
        if not current_user.is_authenticated and request.endpoint not in ['common.login']:
            return redirect(url_for('common.login'))

    with app.app_context():
        from app.routes import register_blueprints
        register_blueprints(app)

    # Импортируем модели после создания приложения и расширений, иначе циклится
    from app import models
    from app.views import InstrumentView, IndexView, RunView, LogoutView

    def format_time(value, _format='%H:%M'):
        """Форматирование даты и времени в указанный формат."""
        if isinstance(value, datetime):
            value += timedelta(hours=3)  # Добавляем 3 часа
            return value.strftime(_format)
        return value  # Если значение не является datetime, возвращаем его без изменений

    def format_currency(value):
        return f"{value:,.0f}"

    # Регистрация фильтра в приложении
    app.jinja_env.filters['time'] = format_time
    app.jinja_env.filters['currency'] = format_currency

    admin = Admin(app, name='FinHub', template_mode='bootstrap3', url='/', index_view=IndexView(url='/'))

    admin.add_view(InstrumentView(app.models.instrument.Instrument, db.session))
    admin.add_view(RunView(app.models.run.Run, db.session))
    admin.add_view(ModelView(app.models.deal.Deal, db.session))
    admin.add_view(LogoutView(name="Logout", endpoint='logout'))

    return app
