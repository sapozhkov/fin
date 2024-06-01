from flask_admin import AdminIndexView, expose
from flask_login import login_required

from common.lib import TinkoffApi
from app.models import Run
from lib.time_helper import TimeHelper


class IndexView(AdminIndexView):
    @staticmethod
    def _get_runs():
        return Run.query.filter(Run.date == TimeHelper.get_current_date()) \
            .order_by(Run.config).all()

    @staticmethod
    def _get_balance():
        return round(TinkoffApi.get_account_balance_rub())

    @expose('/')
    @login_required
    def index(self):
        return self.render('admin/index.html', runs=self._get_runs(), balance=self._get_balance())

    @expose('/get_runs')
    @login_required
    def get_runs(self):
        return self.render('admin/run_table.html', runs=self._get_runs(), balance=self._get_balance())
