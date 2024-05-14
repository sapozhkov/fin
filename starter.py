import asyncio
import datetime
import os
from dotenv import load_dotenv

from dto.config_dto import ConfigDTO
from lib.time_helper import TimeHelper
from test_env.test_alg import TestAlgorithm

load_dotenv()
TOKEN = os.getenv("INVEST_TOKEN")

date = TimeHelper.get_next_date() if TimeHelper.is_evening() else TimeHelper.get_current_date()
if not TimeHelper.is_working_day(date):
    print(f'{datetime.datetime.now()} Выходной, спим')
    exit()


async def run_command(command):
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    # Не ждем завершения процесса

    print(f'Run "{command}", pid {process.pid}')

    return process

current_dir = os.path.dirname(os.path.abspath(__file__))
config_list: list[ConfigDTO] = [
    ConfigDTO.from_repr_string('DELI+ 3/pre6:-3/3 x l2 x 1.6¤ |u0.0 d0.02|'),
    ConfigDTO.from_repr_string('ETLN- 3/pre4:0/2 x l10 x 1.0¤ |u0.0 d0.02|'),
    ConfigDTO.from_repr_string('EUTR+ 3/pre3:-3/3 x l2 x 0.8¤ |u0.0 d0.02|'),
    ConfigDTO.from_repr_string('RNFT+ 3/pre5:3/2 x l2 x 1.4¤ |u0.0 d0.02|'),
    ConfigDTO.from_repr_string('SPBE- 3/pre6:0/2 x l10 x 1.8¤ |u0.0 d0.02|'),
]

# print(config_list)
# exit()


async def main():
    commands = []
    for conf in config_list:

        # вот сюда втыкаем выбор лучшего конфига по текущему
        test_alg = TestAlgorithm(
            TOKEN,
            do_printing=False,
            config=conf,
        )

        print(f"{datetime.datetime.now()} Анализ {conf}")

        if conf.pretest_type == ConfigDTO.PRETEST_PRE:
            pretest_freq = 1
            pretest_days = conf.pretest_period
        else:
            pretest_freq = 0
            pretest_days = 0

        best_conf = test_alg.make_best_config(
            start_date=TimeHelper.get_current_date(),
            test_date=TimeHelper.get_current_date(),
            auto_conf_days_freq=pretest_freq,
            auto_conf_prev_days=pretest_days,
            original_config=conf,
            # и предыдущего конфига нет, это на будущее, когда база будет
            last_config=None
        )

        print(f"{datetime.datetime.now()} Выбран {best_conf}")
        print('')

        commands.append(f"python3 {current_dir}/bot.py {best_conf.to_string()} >> log/all.log 2>&1")

    for command in commands:
        tasks = [run_command(command)]
        await asyncio.gather(*tasks)

print(f'start {datetime.datetime.now()}')

asyncio.run(main())

print(f'stop {datetime.datetime.now()}')
print()
