from flask import redirect, url_for
from flask_admin import BaseView, expose


class LogoutView(BaseView):
    @expose('/')
    def index(self):
        return redirect(url_for('common.logout'))
