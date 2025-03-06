import os
from pathlib import Path

from flask_admin import expose, BaseView
from flask import redirect, url_for, render_template, request, abort
from sqlalchemy.orm import joinedload

from app import AppConfig
from app.config import RunConfig
from app.models import AccRun, Account, Run


class ChartsView(BaseView):
    # Главная страница вьюшки
    @expose('/')
    def index(self):
        return redirect(url_for('admin.index'))

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

    # Страница для вывода логов
    @expose('/run_log/<int:run_id>/')
    def run_log(self, run_id):
        run = Run.query.get_or_404(run_id)

        config_dto = RunConfig.from_repr_string(run.config)
        instrument = run.get_instrument()

        title = f"{run}"

        log_name = config_dto.name or config_dto.ticker
        if instrument:
            log_name = f"{instrument.account_rel.name}_{log_name}"

        log_date = run.date.strftime('%Y.%m.%d')
        if AppConfig.DEBUG_MODE:
            log_root_dir = AppConfig.BASE_DIR
        else:
            log_root_dir = os.path.dirname(AppConfig.BASE_DIR)
        log_root_dir += '/log'
        log_root_dir = Path(log_root_dir).resolve()  # Приводим базовый путь к абсолютному

        log_file_name = f"{log_date}/{log_name}.log"

        file_path = (log_root_dir / log_file_name).resolve()  # Формируем путь к файлу и приводим его к абсолютному

        # Проверяем, что файл действительно внутри base_dir
        if not file_path.is_file() or log_root_dir not in file_path.parents:
            abort(404)

        log_file_path = Path(file_path)  # Преобразуем строку в объект Path

        text = log_file_path.read_text(encoding='utf-8')  # Читаем весь файл в переменную

        return self.render(
            'admin/log.html',
            title=title,
            file_name=log_file_name,
            text=text,
        )
