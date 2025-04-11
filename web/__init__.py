import os

from flask import redirect, url_for, request, session
from flask_admin import Admin
from flask_admin.menu import MenuLink
# from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, current_user

from app import db, AppConfig
from app.models import User
from web.formater import (view_format_datetime, format_currency, format_time, format_currency_class,
                          format_status_class, nl2br)

login = LoginManager()
login.login_view = 'common.login'


@login.user_loader
def load_user(user_id):
    if user_id == "1":
        return User()
    return None


def create_web(app):
    with app.app_context():
        # --- Установка темы по умолчанию (как было до cookie) ---
        app.config['FLASK_ADMIN_SWATCH'] = 'cosmo' if app.config['DEBUG_MODE'] else 'cerulean'
        # --- Конец установки темы по умолчанию ---

        app.template_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
        app.static_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')
        app.static_url_path = '/static'

        login.init_app(app)

        # Обработчик для установки темы перед каждым запросом
        @app.before_request
        def set_theme_from_cookie():
            user_theme_cookie = request.cookies.get('user_theme')
            if user_theme_cookie == 'dark':
                app.config['FLASK_ADMIN_SWATCH'] = 'slate' if app.config['DEBUG_MODE'] else 'darkly'
            elif user_theme_cookie == 'light':
                # Если выбрана светлая, используем стандартные светлые
                app.config['FLASK_ADMIN_SWATCH'] = 'cosmo' if app.config['DEBUG_MODE'] else 'cerulean'
            # Если cookie нет или значение некорректно, используется тема по умолчанию,
            # установленная при инициализации приложения.

        # Проверка авторизации перед каждым запросом,
        # а определение @login.user_loader лежит в моделях
        @app.before_request
        def require_login():
            if (not current_user.is_authenticated and request.endpoint
                    not in ['common.login', 'static', 'common.set_theme']):
                return redirect(url_for('common.login'))

        @app.context_processor
        def inject_favicon_path():
            return {'favicon_path': '/static/favicon/favicon_' + ('dev' if AppConfig.DEBUG_MODE else 'prod') + '.ico'}

        # Импортируем модели после создания приложения и расширений, иначе циклится
        from web.routes import register_blueprints
        from web.views import AccountView, AccRunView, AccRunBalanceView, \
            InstrumentView, InstrumentLogView, IndexView, RunView, TaskView, CommandView, \
            ChartsView, ServerView
        from app.models import Account, AccRun, Run, Instrument, InstrumentLog, Task, Command

        register_blueprints(app)

        # Регистрация фильтра в приложении
        app.jinja_env.filters['time'] = format_time
        app.jinja_env.filters['currency'] = format_currency
        app.jinja_env.filters['currency_class'] = format_currency_class
        app.jinja_env.filters['status_class'] = format_status_class
        app.jinja_env.filters['nl2br'] = nl2br

        admin = Admin(app, name='FinHub', template_mode='bootstrap3', url='/', index_view=IndexView(url='/'))

        admin.add_view(ChartsView(name="Charts"))

        admin.add_view(AccountView(Account, db.session))
        admin.add_view(AccRunView(AccRun, db.session))

        admin.add_view(InstrumentView(Instrument, db.session))
        admin.add_view(RunView(Run, db.session, name="Inst Run"))
        # admin.add_view(ModelView(Deal, db.session))

        admin.add_view(TaskView(Task, db.session))
        admin.add_view(CommandView(Command, db.session))
        # admin.add_view(AccRunBalanceView(AccRunBalance, db.session))
        admin.add_view(InstrumentLogView(InstrumentLog, db.session, name="ILog"))
        admin.add_view(ServerView(name='Server'))
        admin.add_link(MenuLink(name='Logout', url='/logout'))

        # for rule in app.url_map.iter_rules():
        #     print(f"Rule: {rule}")
        #     print(f"Endpoint: {rule.endpoint}")
        #     print(f"Methods: {', '.join(rule.methods)}")
        #     print()

        return app
