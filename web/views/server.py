from flask_admin import BaseView, expose

from app.utils import SystemMonitor


class ServerView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/server.html', content=SystemMonitor.collect_info())
