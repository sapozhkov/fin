import psutil
from urllib.parse import urlparse
from app import AppConfig


class SystemMonitor:
    @staticmethod
    def get_cpu_info():
        # Получение информации о CPU
        cpu_usage = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)
        return f"CPU usage: {cpu_usage}%\nCPU cores: {cpu_count}\n"

    @staticmethod
    def get_memory_info():
        # Получение информации о RAM
        memory = psutil.virtual_memory()
        return (f"Total Memory: {memory.total / (1024 ** 3):.2f} GB\n"
                f"Available Memory: {memory.available / (1024 ** 3):.2f} GB\n"
                f"Used Memory: {memory.used / (1024 ** 3):.2f} GB\n"
                f"Memory Usage: {memory.percent}%\n")

    @staticmethod
    def get_disk_info():
        # Получение информации о дисковом пространстве
        disk = psutil.disk_usage('/')
        return (f"Total Disk Space: {disk.total / (1024 ** 3):.2f} GB\n"
                f"Used Disk Space: {disk.used / (1024 ** 3):.2f} GB\n"
                f"Free Disk Space: {disk.free / (1024 ** 3):.2f} GB\n"
                f"Disk Usage: {disk.percent}%\n")

    @staticmethod
    def get_postgres_info():
        try:
            import psycopg2

            # Парсим URL для получения компонентов подключения
            result = urlparse(AppConfig.SQLALCHEMY_DATABASE_URI)
            username = result.username
            password = result.password
            database = result.path[1:]  # Убираем ведущий слэш
            hostname = result.hostname
            port = result.port if result.port else 5432

            # Подключение к базе данных
            conn = psycopg2.connect(
                dbname=database,
                user=username,
                password=password,
                host=hostname,
                port=port
            )
            cursor = conn.cursor()

            # Запрос размера базы данных
            cursor.execute("SELECT pg_size_pretty(pg_database_size(%s));", (database,))
            db_size = cursor.fetchone()[0]

            # Запрос количества активных подключений
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = %s;", (database,))
            connections = cursor.fetchone()[0]

            # Закрываем соединение
            cursor.close()
            conn.close()

            return (f"Database Size: {db_size}\n"
                    f"Active Connections: {connections}\n")

        except Exception as e:
            return f"Ошибка при получении информации о базе данных PostgreSQL: {e}\n"

    @staticmethod
    def collect_info():
        # Собираем информацию в одну строку
        info = "=== CPU Information ===\n"
        info += SystemMonitor.get_cpu_info()
        info += "\n=== Memory Information ===\n"
        info += SystemMonitor.get_memory_info()
        info += "\n=== Disk Information ===\n"
        info += SystemMonitor.get_disk_info()

        if not AppConfig.DEBUG_MODE:
            info += "\n=== PostgreSQL Information ===\n"
            info += SystemMonitor.get_postgres_info()

        return info
