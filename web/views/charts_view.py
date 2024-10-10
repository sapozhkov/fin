from flask_admin import expose, BaseView
from flask import redirect, url_for, render_template, request
from sqlalchemy.orm import joinedload

from app.models import AccRun, Account, Run


class ChartsView(BaseView):
    # Главная страница вьюшки
    @expose('/')
    def index(self):
        return redirect(url_for('accrun.edit_view'))

    # Страница для отображения графика
    @expose('/balance/<int:acc_run_id>/')
    def balance(self, acc_run_id):
        # Извлечение данных для графика
        chart_url = url_for('common.img_balance_chart', acc_run_id=acc_run_id)

        # Извлечение текущего запуска
        acc_run = AccRun.query.get_or_404(acc_run_id)

        # Получение всех запусков для аккаунта на текущий день
        acc_run_list = (
            AccRun.query
            .join(AccRun.account_rel)  # Присоединяем таблицу Account
            .filter(AccRun.date == acc_run.date)
            .options(joinedload(AccRun.account_rel))  # Загрузка связанных данных
            .order_by(Account.name.asc())  # Сортировка по имени аккаунта
            .all()
        )
        # Выбор предыдущей и следующей даты
        prev_run = AccRun.query.filter(AccRun.account == acc_run.account, AccRun.date < acc_run.date).order_by(
            AccRun.date.desc()).first()
        next_run = AccRun.query.filter(AccRun.account == acc_run.account, AccRun.date > acc_run.date).order_by(
            AccRun.date.asc()).first()

        return self.render(
            'admin/acc_balance.html',
            chart_url=chart_url,
            prev_run=prev_run,
            next_run=next_run,
            acc_run=acc_run,
            acc_run_list=acc_run_list,
        )

    # Страница для отображения графика
    @expose('/run/<int:run_id>/')
    def run(self, run_id):
        # Извлечение данных для графика
        chart_url = url_for('common.img_run_chart', run_id=run_id)

        # Извлечение текущего запуска
        run = Run.query.get_or_404(run_id)

        return self.render(
            'admin/run.html',
            chart_url=chart_url,
            run=run,
        )
