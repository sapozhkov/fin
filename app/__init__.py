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
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

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

    # Импортируем модели после создания приложения и расширений, иначе циклится
    from app import models

    admin = Admin(app, name='FinHub', template_mode='bootstrap3', url='/', index_view=IndexView(url='/'))

    # Добавьте модели в админку
    admin.add_view(ModelView(models.Instrument, db.session))
    admin.add_view(ModelView(models.Run, db.session))
    admin.add_view(ModelView(models.Deal, db.session))
    admin.add_view(LogoutView(name="Logout", endpoint='logout'))

    return app
