from tinkoff.invest import OrderDirection

from app import db
from app.models import Order


# todo move
class HistoricalTrade:
    """
    Класс для работы с историей сделок.
    """

    TYPE_BUY = OrderDirection.ORDER_DIRECTION_BUY
    TYPE_SELL = OrderDirection.ORDER_DIRECTION_SELL

    @staticmethod
    def add_deal(run_id, type_, datetime_, price, count, commission, total):
        order = Order(
            run=run_id,
            type=type_,
            datetime=datetime_,
            price=price,
            commission=commission,
            total=total,
            count=count
        )

        db.session.add(order)
        db.session.commit()

    @staticmethod
    def get_deals(run_id: int) -> list[Order]:
        """Получение сделок за для указанного запуска"""

        return db.session.query(Order).filter(
            Order.run == run_id,
        ).order_by(Order.datetime).all()
