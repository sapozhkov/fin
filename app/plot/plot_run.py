import io
from datetime import timedelta, datetime
from collections import defaultdict
from typing import List, Tuple

from flask import Response, abort
from matplotlib import pyplot as plt, dates as mdates

from app import AppConfig
from app.config import RunConfig
from app.constants import HistoryOrderType
from app.helper import q2f, TimeHelper
from app.models import Order, Run
from app.cache import TickerCache


class PlotRun:
    MAX_LINE_INTERVAL_MINUTES = 3  # Максимальный интервал для склейки ордеров в линию

    @staticmethod
    def _prepare_orders(orders: List[Order]) -> List[Tuple[Order, bool]]:
        """
        Подготавливает ордера для отображения, группируя последовательные ордера одного типа и цены.
        Возвращает список кортежей (ордер, is_line), где is_line указывает, что это часть линии.
        """
        # Группируем ордера по типу и цене
        grouped_orders = defaultdict(list)
        for order in orders:
            key = (order.type, abs(order.price))
            grouped_orders[key].append(order)

        result = []
        for key, group in grouped_orders.items():
            # Сортируем по времени
            group.sort(key=lambda x: x.datetime)
            
            i = 0
            while i < len(group):
                current = group[i]
                # Проверяем, есть ли последовательные ордера
                line_points = [current]
                j = i + 1
                while j < len(group):
                    time_diff = (group[j].datetime - group[j-1].datetime).total_seconds() / 60
                    if (time_diff <= PlotRun.MAX_LINE_INTERVAL_MINUTES and 
                        group[j].type == current.type and 
                        abs(group[j].price) == abs(current.price)):
                        line_points.append(group[j])
                        j += 1
                    else:
                        break
                
                if len(line_points) > 1:
                    # Добавляем первый ордер как точку
                    result.append((line_points[0], False))
                    # Добавляем остальные как линию
                    for point in line_points[1:]:
                        result.append((point, True))
                else:
                    result.append((current, False))
                
                i = j

        return result

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

        last_time = candles.candles[-1].time.strftime('%H:%M') if candles.candles else ''

        # Визуализация
        fig, ax = plt.subplots(figsize=(11, 5))

        # Построение графика изменения цены закрытия
        plt.plot(times, close_prices, label='Close Price', alpha=0.75)
        plt.grid(True)

        # Подготавливаем ордера
        prepared_orders = PlotRun._prepare_orders(orders)

        labels_added = set()
        line_segments = defaultdict(list)  # Для хранения сегментов линий по типу и цене

        for order, is_line in prepared_orders:
            label_title, color, marker = HistoryOrderType.get_plot_settings(order.type)
            executed = order.type in HistoryOrderType.EXECUTED_TYPES

            if is_line:
                # Собираем точки для линии
                line_segments[(order.type, abs(order.price))].append((order.datetime + t_shift, abs(order.price)))
            else:
                # Отображаем точку
                label = label_title if order.type not in labels_added else ""
                plt.scatter(order.datetime + t_shift, abs(order.price),
                          color=color, marker=marker, alpha=.5 if executed else .1, s=50, label=label)
                labels_added.add(order.type)

        # Отображаем линии
        for (order_type, price), points in line_segments.items():
            if len(points) > 1:
                label_title, color, _ = HistoryOrderType.get_plot_settings(order_type)
                times, prices = zip(*points)
                # Рисуем одну линию от первой до последней точки
                plt.plot([times[0], times[-1]], [prices[0], prices[-1]], 
                        color=color, alpha=0.3, linestyle='-', linewidth=2)

        # Добавление вертикальных линий для начала и конца аукционов
        for time in TimeHelper.WEEKEND_BREAKS if TimeHelper.is_weekend(date) else TimeHelper.WORKDAY_BREAKS:
            if last_time and time > last_time:
                continue
            time_stamp = (datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M") + t_shift)
            time_stamp_num = mdates.date2num(time_stamp)
            plt.axvline(x=time_stamp_num, color='blue', linestyle='--', alpha=0.3)

        # Форматирование оси времени
        ax.xaxis_date()
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

        plt.xticks(rotation=45)
        if title:
            plt.title(title)
        plt.legend()
        plt.tight_layout()
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

        plot = cls._get_plot(config.ticker, f"{run.date}", orders)

        # Сохранение в буфер как PNG
        buf = io.BytesIO()
        plot.savefig(buf, format='png')
        plot.close()  # Закрыть фигуру, чтобы не было утечки памяти
        buf.seek(0)

        # Возвращаем изображение как ответ
        return Response(buf, mimetype='image/png')
