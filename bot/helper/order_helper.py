from tinkoff.invest import PostOrderResponse, OrderState

from app.helper import q2f


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
        if isinstance(order, PostOrderResponse):
            price = q2f(order.executed_order_price)
        elif isinstance(order, OrderState):
            price = q2f(order.average_position_price)
        else:
            raise TypeError

        if price > 0:
            return price

        return q2f(order.initial_security_price)

    @staticmethod
    def get_lots(order: PostOrderResponse | OrderState) -> int:
        """
        Отдает количество лотов в заказе.
        Отдает округленное частное от общей суммы и цены за 1 -
        это для расчета реального количества с учетом лотностей инструмента и алгоритма
        :param order:
        :return:
        """
        return round(q2f(order.initial_order_price) / OrderHelper.get_avg_price(order))

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
