import matplotlib.pyplot as plt
import io
from flask import Response
from matplotlib.ticker import MaxNLocator
from app import AppConfig
from app.models import AccRunBalance
from datetime import timedelta


class PlotBalance:
    @staticmethod
    def _get_plot(acc_run_id: int) -> plt:
        # Получаем данные для указанного acc_run
        balances = AccRunBalance.query.filter_by(acc_run=acc_run_id).order_by(AccRunBalance.datetime).all()

        # Фильтруем нулевые значения
        filtered_balances = [
            b for b in balances if b.balance != 0
        ]

        # Сдвигаем время на 3 часа
        times = [(b.datetime + timedelta(hours=AppConfig.TIME_SHIFT_HOURS)).strftime('%H:%M') for b in filtered_balances]
        values = [b.balance for b in filtered_balances]

        # Построение графика
        plt.figure(figsize=(10, 5))
        plt.plot(times, values, marker='.')
        plt.grid(True)

        # Наклон подписей на 45 градусов
        plt.xticks(rotation=45)

        # Ограничение количества вертикальных линий (меток)
        plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True, prune='both'))

        # Добавление горизонтальных линий с процентным изменением
        if values:
            start_value = values[0]

            # Вычисление процентных изменений
            max_change = ((max(values) - start_value) / start_value) * 100
            min_change = ((min(values) - start_value) / start_value) * 100
            end_change = ((values[-1] - start_value) / start_value) * 100

            plt.axhline(y=max(values), color='m', linestyle='--',
                        label=f'High: {max(values):.2f} ({max_change:+.2f}%)')
            plt.axhline(y=start_value, color='g', linestyle='--',
                        label=f'Open: {start_value:.2f}')
            plt.axhline(y=values[-1], color='r', linestyle='--',
                        label=f'Close: {values[-1]:.2f} ({end_change:+.2f}%)')
            plt.axhline(y=min(values), color='b', linestyle='--',
                        label=f'Low: {min(values):.2f} ({min_change:+.2f}%)')

            plt.legend()

        return plt

    @classmethod
    def draw_web(cls, acc_run_id: int):
        plot = cls._get_plot(acc_run_id)

        # Сохранение в буфер как PNG
        buf = io.BytesIO()
        plot.savefig(buf, format='png')
        plot.close()  # Закрыть фигуру, чтобы не было утечки памяти
        buf.seek(0)

        # Возвращаем изображение как ответ
        return Response(buf, mimetype='image/png')
