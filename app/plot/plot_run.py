import io
from datetime import timedelta

from flask import Response, abort
from matplotlib import pyplot as plt, dates as mdates

from app import AppConfig
from app.config import RunConfig
from app.constants import HistoryOrderType
from app.helper import q2f
from app.models import Order, Run
from bot.instrument_cache import TickerCache


class PlotRun:
    @staticmethod
    def _get_plot(ticker: str, date: str, orders: list[Order] = list, title=None) -> plt:
        """
        Приватный метод формирует само изображение, проброс его на соответствующий выход идет в других методах
        """

        ticker_cache = TickerCache(ticker)
        candles = ticker_cache.get_candles(date)

        # Подготовка данных для графика
        t_shift = timedelta(hours=AppConfig.TIME_SHIFT_HOURS)
        times = [(candle.time + t_shift) for candle in candles.candles]  # Время каждой свечи
        close_prices = [q2f(candle.close) for candle in candles.candles]  # Цены закрытия каждой свечи

        # Визуализация
        fig, ax = plt.subplots(figsize=(11, 5))

        # Построение графика изменения цены закрытия
        plt.plot(times, close_prices, label='Close Price', alpha=0.75)

        # # бары
        # low_prices = [q2f(candle.low) for candle in candles.candles]
        # high_prices = [q2f(candle.high) for candle in candles.candles]
        # plt.plot([times, times], [low_prices, high_prices], color='grey', linewidth=1)

        labels_added = set()
        for order in orders:
            label_title, color, marker = HistoryOrderType.get_plot_settings(order.type)

            executed = order.type in HistoryOrderType.EXECUTED_TYPES

            label = label_title if order.type not in labels_added else ""
            plt.scatter(order.datetime + t_shift, abs(order.price),
                        color=color, marker=marker, alpha=.5 if executed else .1, s=50, label=label)

            # Помечаем метку как добавленную
            labels_added.add(order.type)

        # Форматирование оси времени
        ax.xaxis_date()  # Интерпретировать ось X как даты
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))  # Интервал в один час
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))  # Формат времени

        plt.xticks(rotation=45)  # Поворот меток времени
        plt.title(title if title else f"Изменение цены закрытия за день")
        plt.xlabel('Время')
        plt.ylabel('Цена закрытия')
        plt.legend()
        plt.tight_layout()  # Автоматическая корректировка подложки
        return plt

    @classmethod
    def draw_notebook(cls, ticker, date, orders: list[Order] = list, title=None):
        plot = cls._get_plot(ticker, date, orders, title)
        plot.show()
        plot.close()

    @classmethod
    def draw_web(cls, run_id: int):
        run = Run.get_by_id(run_id)

        if not run:
            abort(404)

        orders = Order.get_by_run_id(run_id)

        config = RunConfig.from_repr_string(run.config)

        plot = cls._get_plot(config.ticker, f"{run.date}", orders, f"{run}")

        # Сохранение в буфер как PNG
        buf = io.BytesIO()
        plot.savefig(buf, format='png')
        plot.close()  # Закрыть фигуру, чтобы не было утечки памяти
        buf.seek(0)

        # Возвращаем изображение как ответ
        return Response(buf, mimetype='image/png')
