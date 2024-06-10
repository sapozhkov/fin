from datetime import datetime

from app import create_app
from app.models import Instrument
from app.tasks import UpdInstrumentTask


def main():

    def print_log(text=''):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {text}" if text else '')

    print_log(f"ДОБАВЛЕНИЕ ЗАДАНИЙ НА ОБНОВЛЕНИЕ ИНСТРУМЕНТОВ")

    # выбираем все инструменты
    instr_list = Instrument.get_all()

    for instrument in instr_list:
        task = UpdInstrumentTask.add(instrument.id)
        if task:
            print_log(f"Для {instrument} добавлен task на обновление {task}")
        else:
            print_log(f"Для {instrument} task не добавлен (уже есть в очереди)")

    print_log()


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        main()
