import asyncio
import datetime
import os

from dto.config_dto import ConfigDTO


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
        commands.append(f"python3 {current_dir}/bot.py {conf.to_string()} >> log/all.log 2>&1")

    for command in commands:
        tasks = [run_command(command)]
        await asyncio.gather(*tasks)

print(f'start {datetime.datetime.now()}')

asyncio.run(main())

print('stop')
