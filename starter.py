import asyncio
import datetime
import os
from dotenv import load_dotenv

from dto.config_dto import ConfigDTO
from lib.time_helper import TimeHelper
from test_env.test_alg import TestAlgorithm

load_dotenv()
TOKEN = os.getenv("INVEST_TOKEN")

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
    ConfigDTO(
    ),
    # ConfigDTO(
    #     step_max_cnt=5,
    #     step_base_cnt=None,
    #     step_size=1.2,
    # ),
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

        print(f"{datetime.datetime.now()} Выбран лучший конфиг {best_conf}")

        commands.append(f"python3 {current_dir}/bot.py {best_conf.to_string()} >> log/all.log 2>&1")

    for command in commands:
        tasks = [run_command(command)]
        await asyncio.gather(*tasks)

print(f'start {datetime.datetime.now()}')

asyncio.run(main())

print('stop')
