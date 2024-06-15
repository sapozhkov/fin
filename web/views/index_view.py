from flask_admin import AdminIndexView, expose
from flask_login import login_required

from app.lib import TinkoffApi
from app.models import Run


class IndexView(AdminIndexView):
    @staticmethod
    def _get_runs_by_acc():
        # список текущих прогонов
        runs = Run.get_current_runs_on_accounts()

        # добавляем баланс
        for run in runs:
            run['balance'] = TinkoffApi.get_account_balance_rub(str(run['account'].id))

        return runs

    @expose('/')
    @login_required
    def index(self):
        return self.render('admin/index.html', accounts=self._get_runs_by_acc())

    @expose('/get_runs')
    @login_required
    def get_runs(self):
        return self.render('admin/run_table.html', accounts=self._get_runs_by_acc())
