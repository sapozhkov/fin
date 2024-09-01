import os
import shutil
import tarfile
from datetime import datetime

from dateutil.relativedelta import relativedelta

# Исходная директория с логами
log_dir = os.path.expanduser("~/log")
# Специальная директория для временного хранения логов перед архивированием
tmp_log_dir = os.path.expanduser("~/log_tmp")
# Директория для хранения созданных архивов
archive_log_dir = os.path.expanduser("~/log_archive")


def ensure_directory_exists(directory_path):
    """
    Проверяет наличие директории, и если она не существует, создаёт её.
    :param directory_path: Путь к директории
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


# Функция для перемещения всех объектов (файлов и директорий)
def move_dir_content(src, dst):
    for m_file_name in os.listdir(src):
        full_file_name = os.path.join(src, m_file_name)
        shutil.move(full_file_name, dst)


# Функция для создания архива
def create_tar_gz(a_file_name, a_source_dir):
    with tarfile.open(a_file_name, "w:gz") as tar:
        tar.add(a_source_dir, arcname=os.path.basename(a_source_dir))


ensure_directory_exists(log_dir)
ensure_directory_exists(tmp_log_dir)
ensure_directory_exists(archive_log_dir)

# Вычисляем предыдущий месяц
previous_month = datetime.now() - relativedelta(months=1)

# Формируем имя архива с предыдущим месяцем в формате "YYYY.MM"
archive_name = os.path.join(archive_log_dir, f"logs_{previous_month.strftime('%Y_%m')}.tar.gz")

if os.path.isfile(archive_name):
    print(f"Архив {archive_name} уже существует.")
    exit()

# Перемещаем файлы
move_dir_content(log_dir, tmp_log_dir)

# Создаем архив
create_tar_gz(archive_name, tmp_log_dir)

# Очищаем спец директорию
for file_name in os.listdir(tmp_log_dir):
    file_path = os.path.join(tmp_log_dir, file_name)
    try:
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.unlink(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        print(f'Ошибка при удалении {file_path}. Причина: {e}')

print("Архивация завершена успешно.")
