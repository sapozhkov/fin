import os
from datetime import datetime, timedelta

from flask import redirect, url_for, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, current_user

from app import db

login = LoginManager()
login.login_view = 'common.login'


def format_time(value, _format='%H:%M'):
    """Форматирование даты и времени в указанный формат."""
    if isinstance(value, datetime):
        value += timedelta(hours=3)  # Добавляем 3 часа
        return value.strftime(_format)
    return value  # Если значение не является datetime, возвращаем его без изменений


def format_currency(value):
    return f"{value:,.0f}"


def create_web(app):
    app.config['FLASK_ADMIN_SWATCH'] = 'cosmo' if app.config['DEBUG_MODE'] else 'cerulean'
    app.template_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')

    login.init_app(app)

    # Проверка авторизации перед каждым запросом,
    # а определение @login.user_loader лежит в моделях
    @app.before_request
    def require_login():
        if not current_user.is_authenticated and request.endpoint not in ['common.login']:
            return redirect(url_for('common.login'))

    # Импортируем модели после создания приложения и расширений, иначе циклится
    from web.routes import register_blueprints
    from web.views import InstrumentView, IndexView, RunView, LogoutView
    from app.models import Run, Instrument, Deal

    register_blueprints(app)

    # Регистрация фильтра в приложении
    app.jinja_env.filters['time'] = format_time
    app.jinja_env.filters['currency'] = format_currency

    admin = Admin(app, name='FinHub', template_mode='bootstrap3', url='/', index_view=IndexView(url='/'))

    admin.add_view(InstrumentView(Instrument, db.session))
    admin.add_view(RunView(Run, db.session))
    admin.add_view(ModelView(Deal, db.session))
    admin.add_view(LogoutView(name="Logout", endpoint='logout'))

    return app
