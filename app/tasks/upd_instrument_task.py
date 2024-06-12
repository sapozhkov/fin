import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

from app import AppConfig
from app.config import RunConfig
from app.constants import TaskStatus
from app.models import Instrument, Task
from app.tasks import AbstractTask
from bot import TestAlgorithm
from bot.vis import TaskProgress


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

        t_config = RunConfig.from_repr_string(instrument.config)

        test_configs = [
            (RunConfig(
                ticker=t_config.ticker,
                step_max_cnt=max_shares,
                step_base_cnt=base_shares,
                step_lots=1,

                majority_trade=t_config.majority_trade,
                pretest_period=pretest_period,
                pretest_type=RunConfig.PRETEST_PRE,

                threshold_buy_steps=0,
                threshold_sell_steps=0,
                stop_up_p=stop_up_p,
                stop_down_p=0,

                step_size=t_config.step_size + step_size_shift,
                step_set_orders_cnt=step_cnt,
            ))
            for max_shares in [3, 4]
            for base_shares in [0]
            for stop_up_p in [0, 0.01]
            for step_size_shift in [0, .2, -.2]
            for step_cnt in [2]
            for pretest_period in range(3, 7)
        ]

        def run_test(config: RunConfig):
            test_alg = TestAlgorithm(do_printing=False, config=config)
            return test_alg.test(
                last_test_date=None,  # будет взята текущая дата
                test_days_num=10,
                shares_count=0,

                auto_conf_days_freq=1,
                auto_conf_prev_days=config.pretest_period,
            )

        unique_configs = set(test_configs)

        results = []

        with ThreadPoolExecutor(max_workers=min(multiprocessing.cpu_count(), 4)) as executor:
            future_to_params = {executor.submit(run_test, config): config for config in unique_configs}

            for future in as_completed(future_to_params):
                res = future.result()
                if res:
                    results.append(res)

        # Вывод результатов или их дальнейшая обработка
        sorted_results = sorted(results, key=lambda x: (x['config'].ticker, -float(x['profit_p'])), reverse=False)

        print()
        for item in sorted_results:
            print(item)

        best_res = sorted_results[0]
        new_config = best_res['config']
        new_profit = int(best_res['profit_p'])

        print(f"Сохраним вот это: {new_config}, profit {new_profit}")

        cur_status = bool(instrument.status)
        new_status = new_profit >= AppConfig.INSTRUMENT_ON_THRESHOLD

        print(f"Порог прибыли {AppConfig.INSTRUMENT_ON_THRESHOLD}, расчетная прибыль {new_profit}")
        if cur_status != new_status:
            print(f"Изменяем статус активности на {new_status}")
            instrument.status = 1 if new_status else 0
        else:
            print("Активность не меняем")

        instrument.config = str(new_config)
        instrument.expected_profit = round(new_profit, 2)
        instrument.save()

        return True
