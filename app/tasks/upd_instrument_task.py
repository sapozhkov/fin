from app import AppConfig
from app.config import RunConfig
from app.constants import TaskStatus
from app.helper import TimeHelper
from app.lib import TinkoffApi
from app.models import Instrument, Task, InstrumentLog
from app.tasks import AbstractTask
from app.cache import TickerCache
from bot.test import TestAlgorithm


class UpdInstrumentTask(AbstractTask):
    @staticmethod
    def make_name(instrument_id: int) -> str:
        return f"instr_{instrument_id}"

    @classmethod
    def add(cls, instrument_id: int) -> Task | None:
        name = cls.make_name(instrument_id)

        task = Task()
        task.status = TaskStatus.PENDING
        task.class_name = f"{cls.__module__}.{cls.__name__}"
        task.name = name
        task.data = str(instrument_id)

        if task.already_exists():
            return None

        task.save()
        return task

    @staticmethod
    def run(task: Task) -> bool:
        # достать из базы инструмент
        instrument = Instrument.get_by_id(int(task.data))

        # его конфиг
        t_config = RunConfig.from_repr_string(instrument.config)

        # выбираем дату. после торгов - следующая, иначе текущий день (в тесте берется от предыдущией даты)
        if TimeHelper.trades_are_finished():
            test_date = TimeHelper.get_next_date()
        else:
            test_date = TimeHelper.get_current_date()

        print(f"Инструмент: {instrument}")
        print(f"Расчет на дату {test_date}, глубина дней: {t_config.pretest_period}")

        # выбираем лучший конфиг
        test_alg = TestAlgorithm(do_printing=False, config=t_config)

        test_alg.update_config(test_date, True)

        add_text = ''
        if test_alg.base_expected_profit is not None:
            new_base_config = test_alg.upd_base_config
            new_base_config.step_lots = 1

            print(f"Исходный (base): {instrument.base_config}")
            print(f"Новый (base):    {new_base_config}, profit {test_alg.base_expected_profit}")

            add_text = f"{instrument.base_config} -> {new_base_config}, expected profit {test_alg.base_expected_profit}"

            instrument.base_config = str(new_base_config)

        new_config = test_alg.config
        new_profit = test_alg.expected_profit

        # приводим лотность к единице, при запуске будет перерасчитана нужная
        new_config.step_lots = 1

        print(f"Исходный: {t_config}")
        print(f"Новый:    {new_config}, profit {new_profit}")

        # анализируем пригодность для запуска. ниже порогового значения - отключаем
        threshold = AppConfig.INSTRUMENT_ON_THRESHOLD
        cur_status = bool(instrument.status)
        new_status = new_profit >= threshold

        print(f"Порог прибыли {threshold}, расчетная прибыль {new_profit}")

        if new_config.mod_do_not_change_instrument_activity:
            if cur_status != new_status:
                print(f"Изменение активности заблокировано модификатором F. instrument.status={instrument.status}, "
                      f"а должен был быть установлен {int(new_status)}")
            else:
                print("Изменение активности заблокировано модификатором F, но менять и не надо")

        else:
            if cur_status != new_status:
                print(f"Изменяем статус активности на {new_status}")
                instrument.status = 1 if new_status else 0
            else:
                print("Активность не меняем")

        # обновляем данные инструмента в базе
        instrument.config = str(new_config)
        instrument.expected_profit = round(new_profit, 2)

        # обновить цену заодно
        ticker_cache = TickerCache(t_config.ticker)
        figi = ticker_cache.get_instrument().figi
        instrument.price = TinkoffApi.get_last_price(figi)

        task.error = (f"{instrument.id} {instrument.account_rel.name} {'On' if instrument.status == 1 else 'Off'} "
                      f"p{instrument.expected_profit}, \n{new_config}")

        instrument.save()

        # и кладем в лог новое значение
        InstrumentLog.add_by_instrument(instrument, add_text)

        return True
