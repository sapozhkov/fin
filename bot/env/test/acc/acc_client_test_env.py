from typing import List

from app.dto import BoughtInstrumentDto
from bot.env import AbstractAccClient
from bot.test import TestAlgorithm


class TestAccClientEnvHelper(AbstractAccClient):
    def __init__(self, bot_alg_list: List[TestAlgorithm]):
        self.bot_alg_list = bot_alg_list

    def get_account_balance_rub(self, account_id: str) -> float:
        sum_balance = 0
        for bot_alg in self.bot_alg_list:
            sum_balance += bot_alg.get_cur_balance()
        return round(sum_balance, 2)

    def get_shares_on_account(self, account_id) -> List[BoughtInstrumentDto]:
        out = []
        for bot_alg in self.bot_alg_list:
            if bot_alg.accounting_helper.get_num() == 0:
                continue
            out.append(BoughtInstrumentDto(
                figi=bot_alg.config.ticker,
                ticker=bot_alg.config.ticker,
                quantity=bot_alg.accounting_helper.get_num()
            ))
        return out

    def sell(self, account_id: str, figi: str, quantity: int):
        # при тестах должно работать с figi = ticker для упрощения логики
        for bot_alg in self.bot_alg_list:
            if bot_alg.config.ticker != figi:
                continue
            if quantity > 0:
                # выполнить команду продажи по текущей цене
                bot_alg.bot.sell(quantity)
