import os

from flask import redirect, url_for, request
from flask_admin import Admin
from flask_admin.menu import MenuLink
# from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, current_user

from app import db
from app.models import User
from web.formater import view_format_datetime, format_currency, format_time

login = LoginManager()
login.login_view = 'common.login'


@login.user_loader
def load_user(user_id):
    if user_id == "1":
        return User()
    return None


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
    from web.views import InstrumentView, IndexView, RunView, TaskView
    from app.models import Run, Instrument, Task

    register_blueprints(app)

    # Регистрация фильтра в приложении
    app.jinja_env.filters['time'] = format_time
    app.jinja_env.filters['currency'] = format_currency

    admin = Admin(app, name='FinHub', template_mode='bootstrap3', url='/', index_view=IndexView(url='/'))

    admin.add_view(InstrumentView(Instrument, db.session))
    admin.add_view(RunView(Run, db.session))
    # admin.add_view(ModelView(Deal, db.session))
    admin.add_view(TaskView(Task, db.session))
    admin.add_link(MenuLink(name='Logout', url='/logout'))

    return app
