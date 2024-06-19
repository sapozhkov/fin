from abc import ABC, abstractmethod


class TradeAbstractStrategy(ABC):
    def __init__(
            self,
            bot
    ):
        self.bot = bot

    @abstractmethod
    def update_orders_status(self):
        pass

    @abstractmethod
    def place_buy_orders(self):
        pass

    @abstractmethod
    def place_sell_orders(self):
        pass
