import time
from datetime import datetime, timedelta


class TaskProgress:
    def __init__(self, total_iterations):
        self.total_iterations = total_iterations
        self.start_time = time.time()
        self.current_iteration = 0

        # Форматирование и вывод времени запуска
        print(f'Запуск в {datetime.now().strftime("%H:%M")}')
        print(f'Инициализация...', end='')

    def update_progress(self, current_iteration: int | None = None):
        self.current_iteration = current_iteration if current_iteration else self.current_iteration + 1

        elapsed_time = time.time() - self.start_time
        avg_iteration_time = elapsed_time / self.current_iteration
        remaining_time = avg_iteration_time * (self.total_iterations - self.current_iteration)
        estimated_end_time = datetime.now() + timedelta(seconds=remaining_time)

        percent_complete = (self.current_iteration / self.total_iterations) * 100

        # Очистка текущей строки в консоли
        print('\r', end='')
        print(f'Выполнено {percent_complete:.0f}% ({self.current_iteration}/{self.total_iterations}), ', end='')

        if self.current_iteration != self.total_iterations:
            print(f'закончим в ~ {estimated_end_time.strftime("%H:%M")}', end='')
        else:
            print(f'закончено в {datetime.now().strftime("%H:%M")}, '
                  f'длительность {timedelta(seconds=time.time() - self.start_time)}', end='\n')
