from tinkoff.invest import Quotation
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from bot.dto import DealDTO, OrderDTO
from lib.ticker_cache import TickerCache
from lib.historical_trade import HistoricalTrade
from lib.order_vis_helper import OrderVisHelper


class Visualize:
    def __init__(self, ticker_cache: TickerCache):
        self.ticker_cache = ticker_cache

    # Функция для преобразования Quotation в float
    @staticmethod
    def q2f(quotation: Quotation, digits=2):
        return round(quotation.units + quotation.nano * 1e-9, digits)

    def draw(self, date, deals: list[DealDTO], orders: list[OrderDTO] = list, title=None):

        candles = self.ticker_cache.get_candles(date)

        # Подготовка данных для графика
        times = [candle.time for candle in candles.candles]  # Время каждой свечи
        close_prices = [self.q2f(candle.close) for candle in candles.candles]  # Цены закрытия каждой свечи

        # Визуализация
        fig, ax = plt.subplots(figsize=(14, 7))

        # Построение графика изменения цены закрытия
        plt.plot(times, close_prices, label='Close Price', alpha=0.75)

        # # бары
        # low_prices = [self.q2f(candle.low) for candle in candles.candles]
        # high_prices = [self.q2f(candle.high) for candle in candles.candles]
        # plt.plot([times, times], [low_prices, high_prices], color='grey', linewidth=1)

        labels_added = set()
        for deal in deals:
            if deal.type == HistoricalTrade.TYPE_BUY:
                # Добавляем метку только если она еще не была добавлена
                label = 'Buy' if deal.type not in labels_added else ""
                plt.scatter(deal.datetime, abs(deal.price), color='blue', marker='^', alpha=.5, s=50, label=label)
            elif deal.type == HistoricalTrade.TYPE_SELL:
                label = 'Sell' if deal.type not in labels_added else ""
                plt.scatter(deal.datetime, abs(deal.price), color='orange', marker='v', alpha=.5, s=50, label=label)

            # Помечаем метку как добавленную
            labels_added.add(deal.type)

        labels_added = set()
        for order in orders:
            label_title, color, marker = OrderVisHelper.get_plot_settings(order.type)

            label = label_title if order.type not in labels_added else ""
            plt.scatter(order.datetime, abs(order.price), color=color, marker=marker, alpha=.5, s=50, label=label)

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
        plt.show()
