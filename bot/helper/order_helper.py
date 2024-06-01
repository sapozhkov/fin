from tinkoff.invest import PostOrderResponse, OrderState

from bot.env import AbstractProxyClient


class OrderHelper:
    def __init__(
            self,
            client: AbstractProxyClient | None = None,
    ):
        self.client = client

    def get_avg_price(self, order: PostOrderResponse | OrderState) -> float:
        """
        Отдает среднюю цену для одного лота в заказе
        Если есть executed - её, нет - вычисляет из initial
        Примеры ответов есть в ClientTestEnvHelper
        :param order:
        :return:
        """
        # executed_order_price - тут лежит средняя цена по API
        lots = OrderHelper.get_lots(order)

        if isinstance(order, PostOrderResponse):
            price = self.client.quotation_to_float(order.executed_order_price)
        elif isinstance(order, OrderState):
            price = self.client.round(self.client.quotation_to_float(order.executed_order_price) / lots)
        else:
            raise TypeError

        if price > 0:
            return price

        # initial_order_price - а вот тут средняя умноженная на лоты
        price = self.client.quotation_to_float(order.initial_order_price)
        return self.client.round(price / lots)

    @staticmethod
    def get_lots(order: PostOrderResponse | OrderState) -> int:
        """
        Отдает количество лотов в заказе.
        Отдает сразу lots_requested - там то, что надо во всех текущих случаях для этого кода
        :param order:
        :return:
        """
        return order.lots_requested

    def get_commission(self, order: PostOrderResponse | OrderState):
        """
        Отдает комиссию для заказа
        Комиссия учитывается полная - для всех лотов в заказе сразу
        API работает по-разному для разных объектов и запросов
        Метод пытается отдать максимально близкое
        Исполнена ли заявка не учитывается
        :param order:
        :return:
        """
        commission = self.client.quotation_to_float(order.executed_commission)
        if commission == 0:
            commission = self.client.quotation_to_float(order.initial_commission)
        return commission
