from tinkoff.invest import PostOrderResponse, OrderState

from app import q2f


class OrderHelper:
    @staticmethod
    def get_avg_price(order: PostOrderResponse | OrderState) -> float:
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
            price = q2f(order.executed_order_price)
        elif isinstance(order, OrderState):
            price = q2f(order.executed_order_price) / lots
        else:
            raise TypeError

        if price > 0:
            return price

        # initial_order_price - а вот тут средняя умноженная на лоты
        price = q2f(order.initial_order_price)
        return price / lots

    @staticmethod
    def get_lots(order: PostOrderResponse | OrderState) -> int:
        """
        Отдает количество лотов в заказе.
        Отдает сразу lots_requested - там то, что надо во всех текущих случаях для этого кода
        :param order:
        :return:
        """
        return order.lots_requested

    @staticmethod
    def get_commission(order: PostOrderResponse | OrderState):
        """
        Отдает комиссию для заказа
        Комиссия учитывается полная - для всех лотов в заказе сразу
        API работает по-разному для разных объектов и запросов
        Метод пытается отдать максимально близкое
        Исполнена ли заявка не учитывается
        :param order:
        :return:
        """
        commission = q2f(order.executed_commission)
        if commission == 0:
            commission = q2f(order.initial_commission)
        return commission
