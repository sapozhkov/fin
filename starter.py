import asyncio
import datetime

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

config_list = [
    ConfigDTO(
        max_shares=4,
        base_shares=-4,
        pretest_period=0,
    ),
    # ConfigDTO(
    #     max_shares=5,
    #     base_shares=None,
    #     step_size=1.2,
    # ),
]


async def main():
    commands = []
    for conf in config_list:
        commands.append(f"python3 trader_bot.py {conf.to_string()}")

    tasks = [run_command(command) for command in commands]
    await asyncio.gather(*tasks)

print(f'start {datetime.datetime.now()}')

asyncio.run(main())

print('stop')
