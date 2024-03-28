import time
from datetime import datetime, timedelta


class TaskProgress:
    def __init__(self, total_iterations):
        self.total_iterations = total_iterations
        self.start_time = time.time()
        self.current_iteration = 0

        print(f'Запуск в {datetime.now().strftime("%H:%M")}')
        print(f'Инициализация...', end='')

    def update_progress(self, current_iteration: int | None = None):
        self.current_iteration = current_iteration if current_iteration else self.current_iteration + 1

        elapsed_time = time.time() - self.start_time
        avg_iteration_time = elapsed_time / self.current_iteration
        remaining_time = avg_iteration_time * (self.total_iterations - self.current_iteration)
        estimated_end_time = datetime.now() + timedelta(seconds=remaining_time)

        percent_complete = (self.current_iteration / self.total_iterations) * 100

        # Расчет длины прогресс-бара
        bar_length = 30
        filled_length = int(round(bar_length * self.current_iteration / float(self.total_iterations)))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        # Очистка текущей строки в консоли и вывод прогресс-бара
        print('\r', end='')
        print(f'[{bar}] {percent_complete:.0f}% ({self.current_iteration}/{self.total_iterations}), '
              f'закончим через {self.get_remaining_time_text(remaining_time)} '
              f'в {estimated_end_time.strftime("%H:%M")}', end='')

        if self.current_iteration == self.total_iterations:
            print('\r' + ' ' * 100, end='\r')
            duration = timedelta(seconds=round(elapsed_time))
            print(f'Закончено в {datetime.now().strftime("%H:%M")}, длительность {duration}', end='\n')

    @staticmethod
    def get_remaining_time_text(remaining_time):
        # Преобразуем секунды в часы, минуты и секунды
        hours, remainder = divmod(remaining_time, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Формируем строку для вывода с учетом наличия часов
        parts = []
        if hours > 0:
            parts.append(f"{int(hours):02}ч")
        if minutes > 0 or hours > 0:  # Выводим минуты, если есть часы или минуты
            parts.append(f"{int(minutes):02}м")
        parts.append(f"{int(seconds):02}с")

        return " ".join(parts[:2]) + ' ' * 10
