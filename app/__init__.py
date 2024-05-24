from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user, login_required
from flask_admin import Admin, AdminIndexView, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from config import Config

# Инициализация расширений
db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'common.login'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['FLASK_ADMIN_SWATCH'] = 'cosmo' if Config.DEBUG_MODE else 'cerulean'

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

    class IndexView(AdminIndexView):
        @expose('/')
        @login_required
        def index(self):
            return self.render(self._template)

    with app.app_context():
        from app.routes import common
        app.register_blueprint(common.bp)

    class LogoutView(BaseView):
        @expose('/')
        def index(self):
            return redirect(url_for('common.logout'))

    class InstrumentView(ModelView):
        column_list = ('id', 'name', 'account', 'config', 'status')
        form_columns = ('name', 'account', 'config', 'status')

    class RunView(ModelView):
        column_filters = (
            'instrument', 'instrument_rel', 'status', 'date'
        )
        column_list = (
            'id', 'instrument_rel', 'date', 'status', 'exit_code', 'last_error', 'total', 'depo',
            'profit', 'data', 'config', 'start_cnt', 'end_cnt', 'candle', 'created_at', 'updated_at')
        form_columns = (
            'instrument_rel', 'date', 'status', 'exit_code', 'last_error', 'total', 'depo',
            'profit', 'data', 'config', 'start_cnt', 'end_cnt', 'candle', 'created_at', 'updated_at')

        def create_form(self, obj=None):
            form = super(RunView, self).create_form()
            form.instrument_rel.query_factory = lambda: models.Instrument.query.all()
            return form

        def edit_form(self, obj=None):
            form = super(RunView, self).edit_form(obj)
            form.instrument_rel.query_factory = lambda: models.Instrument.query.all()
            return form

    # Импортируем модели после создания приложения и расширений, иначе циклится
    from app import models

    admin = Admin(app, name='FinHub', template_mode='bootstrap3', url='/', index_view=IndexView(url='/'))

    # Добавьте модели в админку
    admin.add_view(InstrumentView(models.Instrument, db.session))
    admin.add_view(RunView(models.Run, db.session))
    admin.add_view(ModelView(models.Deal, db.session))
    admin.add_view(LogoutView(name="Logout", endpoint='logout'))

    return app
