import asyncio
import datetime
import os
from collections import defaultdict
from time import sleep

from sqlalchemy.orm import joinedload

from app import create_app, AppConfig, db
from app.lib import TinkoffApi
from app.models import Instrument, Run, Account
from app.config import RunConfig, AccConfig
from bot.db import TickerCache
from app.helper import TimeHelper
from bot import TestAlgorithm

date = TimeHelper.get_next_date() if TimeHelper.is_evening() else TimeHelper.get_current_date()
if not TimeHelper.is_working_day(date):
    print(f'{datetime.datetime.now()} Выходной, спим')
    exit()


async def run_command(command):
    print(command)

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    # Не ждем завершения процесса

    print(f'Running on pid {process.pid}')

    return process


class Stock:
    instrument_id: int = 0
    config: RunConfig
    ticker: str = ''
    figi: str = ''
    price: float = 0
    budget: float = 0
    lots: int = 0

    def __repr__(self):
        return f"{self.config} p{self.price} b{self.budget} l{self.lots}"


def distribute_budget(stocks: list[Stock], budget):
    # Сортируем акции по минимальной стоимости портфеля
    stocks.sort(key=lambda s: s.budget, reverse=True)

    # result = {stock: 0 for stock in stocks}
    remaining_budget = budget

    # Вычисляем равную долю бюджета для каждой акции
    equal_share = budget / len(stocks)

    # Распределяем равную долю бюджета для каждой акции
    for stock in stocks:
        # Количество акций, которые можно купить за бюджет
        count = int(equal_share // stock.budget)
        stock.lots = count
        remaining_budget -= count * stock.budget

    max_iterations = 3

    for i in range(1, max_iterations+1):
        for stock in stocks:
            if remaining_budget < stock.budget:
                continue

            # на последней итерации "сколько влезает", а так по одному шагу добавляем
            count = int(remaining_budget // stock.budget) if i == max_iterations else 1

            stock.lots += count
            remaining_budget -= count * stock.budget

    # обновляем конфиги
    for stock in stocks:
        stock.config.step_lots = stock.lots


def get_best_config(stock):
    conf = stock.config

    # вот сюда втыкаем выбор лучшего конфига по текущему
    test_alg = TestAlgorithm(
        do_printing=False,
        config=conf,
    )

    if conf.pretest_type == RunConfig.PRETEST_PRE:
        pretest_freq = 1
        pretest_days = conf.pretest_period
    else:
        pretest_freq = 0
        pretest_days = 0

    print(f"{datetime.datetime.now()} Анализ {conf}")

    last_config = None
    prev_run = Run.get_prev_run(stock.instrument_id)
    if prev_run:
        try:
            last_config = RunConfig.from_repr_string(prev_run.config)
            print(f"{datetime.datetime.now()} + пред {last_config} от {prev_run.date}")
        except ValueError:
            print(f"Не удалось разобрать конфиг {prev_run}")

    best_conf, profit_p = test_alg.make_best_config_with_profit(
        start_date=TimeHelper.get_current_date(),
        test_date=TimeHelper.get_current_date(),
        auto_conf_days_freq=pretest_freq,
        auto_conf_prev_days=pretest_days,
        original_config=conf,
        last_config=last_config
    )

    print(f"{datetime.datetime.now()} Выбран {best_conf} с прибылью {profit_p}")
    print('')

    return best_conf


async def main():
    app = create_app()
    with app.app_context():
        commands = []
        commands_acc = []
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # набор инструментов
        instruments = Instrument.query.join(Account).filter(
            Instrument.status == 1,
            Account.status == 1
        ).options(joinedload(Instrument.account_rel)).all()

        # Сгруппируем инструменты по полю account
        grouped_instruments = defaultdict(list)
        for instrument in instruments:
            grouped_instruments[instrument.account].append(instrument)

        for account_id, instruments in grouped_instruments.items():
            account = instruments[0].account_rel
            print(f"Account ID: {account_id}, {account.name}")
            print()

            stocks = []
            for instrument in instruments:
                print(f"Instrument ID: {instrument.id}, Name: {instrument.name}")
                config = RunConfig.from_repr_string(instrument.config)
                ticker = config.ticker
                ticker_cache = TickerCache(ticker)
                figi = ticker_cache.get_instrument().figi

                stock = Stock()
                stock.instrument_id = instrument.id
                stock.config = config
                stock.ticker = ticker
                stock.figi = figi

                stocks.append(stock)

            print()

            # определение лучшего конфига
            for stock in stocks:

                best_conf = get_best_config(stock)

                # проброс в конфиг значения номера инструмента (будет привязка при запуске)
                best_conf.instrument_id = stock.instrument_id

                stock.config = best_conf

            # последние цены и базовый бюджет
            last_prices = TinkoffApi.get_last_prices(figi_list=[s.figi for s in stocks])
            for s in stocks:
                if s.figi in last_prices:
                    price = last_prices[s.figi]
                    maj_k = 2 if s.config.majority_trade else 1

                    s.price = price
                    s.budget = round(price * s.config.step_max_cnt * maj_k, 2)

            # отфильтровываем нулевые цены
            stocks = [stock for stock in stocks if stock.price != 0]

            # баланс целевого аккаунта
            balance = TinkoffApi.get_account_balance_rub(account_id)
            print(f"Баланс {balance}")

            # коррекция суммы
            balance *= AppConfig.ACC_BALANCE_CORRECTION
            print(f"Баланс с коррекцией {balance}")

            if balance <= 0:
                print(f"Баланс с меньше 0, выходим")
                continue

            # распределение ресурсов
            distribute_budget(stocks, balance)

            # отфильтровываем с нулем лотов
            stocks = [stock for stock in stocks if stock.lots != 0]

            sum_used = round(sum([stock.lots * stock.budget for stock in stocks]))

            for stock in stocks:
                print(f"{stock.config.ticker}: {stock.lots} lots * {stock.config.step_max_cnt} steps * {stock.price} "
                      f"= {round(stock.budget * stock.lots, 2)}")

            print(f"Запланировано использование бюджета {sum_used} / {round(balance)} "
                  f"({round(sum_used / balance, 2)}%)")
            print()

            print('Конфигурации на запуск')
            for stock in stocks:
                print(stock)
            print()

            for stock in stocks:
                commands.append(f"python3 {current_dir}/bot.py {stock.config.to_string()} >> ~/log/all.log 2>&1")

            if len(stocks) > 0:
                if not account.config:
                    acc_config = AccConfig(
                        account_id=account.id,
                        name=account.name,
                    )
                    account.config = str(acc_config)
                    db.session.add(account)
                    db.session.commit()

                acc_config = AccConfig.from_repr_string(account.config)
                commands_acc.append(f"python3 {current_dir}/acc_bot.py {acc_config.to_string()} >> ~/log/all.log 2>&1")

        for command in commands:
            tasks = [run_command(command)]
            await asyncio.gather(*tasks)

        # дождемся пока все прогрузятся и забьют себе место в базе
        sleep(20)

        for command in commands_acc:
            tasks = [run_command(command)]
            await asyncio.gather(*tasks)


if __name__ == '__main__':
    print(f'start {datetime.datetime.now()}')

    asyncio.run(main())

    print(f'stop {datetime.datetime.now()}')
    print()
