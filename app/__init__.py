from datetime import datetime, timedelta

from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_required
from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView

from app.constants.run_status import RunStatus
from app.config.app_config import AppConfig

# Инициализация расширений
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
        from app.routes import common
        app.register_blueprint(common.bp)

    # Импортируем модели после создания приложения и расширений, иначе циклится
    from app import models
    from app.views.index_view import IndexView
    from app.views.instrument_view import InstrumentView
    from app.views.run_view import RunView
    from app.views.logout_view import LogoutView

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

    # Добавьте модели в админку
    admin.add_view(InstrumentView(models.Instrument, db.session))
    admin.add_view(RunView(models.Run, db.session))
    admin.add_view(ModelView(models.Deal, db.session))
    admin.add_view(LogoutView(name="Logout", endpoint='logout'))

    return app
