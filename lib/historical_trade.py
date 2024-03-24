from datetime import datetime
import sqlite3
from itertools import groupby

from tinkoff.invest import OrderDirection

from dto.deal_dto import DealDTO
from dto.historical_trade_dto import HistoricalTradeDTO


class HistoricalTrade:
    TYPE_BUY = OrderDirection.ORDER_DIRECTION_BUY
    TYPE_SELL = OrderDirection.ORDER_DIRECTION_SELL

    def __init__(self):
        self.db_file = './db/trading_bot.db'
        self.create_table_if_not_exists()

    def create_table_if_not_exists(self):
        # Подключение к базе данных (файл будет создан, если не существует)
        conn = sqlite3.connect(self.db_file)

        # Создание курсора
        cursor = conn.cursor()

        # Создание таблицы сделок
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY,
            algorithm_name TEXT NOT NULL,
            type INTEGER NOT NULL,
            instrument TEXT NOT NULL,
            datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
            price REAL NOT NULL,
            commission REAL NOT NULL,
            total REAL NOT NULL
        )
        ''')

        # Создание индексов
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_instrument_datetime ON deals (algorithm_name, datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_datetime ON deals (datetime)')

        # Закрытие соединения
        conn.close()

    def clear_table(self):
        """Очистка базы"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
        DELETE FROM deals WHERE 1
        ''')

        conn.close()

    def add_deal(self, algorithm_name, type_, instrument, price, commission, total):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO deals (algorithm_name, type, instrument, price, commission, total)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (algorithm_name, type_, instrument, price, commission, total))
        conn.commit()
        conn.close()

    def get_daily_totals(self, date=None, alg_name: str | None = None) -> list[HistoricalTradeDTO]:
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Получаем аггрегированные данные по дням и algorithm_name
        query = '''
        SELECT 
            algorithm_name, 
            strftime('%Y-%m-%d', SUBSTR(datetime, 1, 19)) AS day,
            SUM(total) AS daily_total,
            count(*) AS cnt
        FROM deals
        WHERE date(SUBSTR(datetime, 1, 19)) = ?
        '''

        params = [date]

        if alg_name:
            query += ' AND algorithm_name = ?'
            params.append(alg_name)

        query += ' GROUP BY algorithm_name, day ORDER BY algorithm_name, day'

        cursor.execute(query, tuple(params))

        aggregated_results = cursor.fetchall()
        results = []

        # Итерация по аггрегированным результатам и выполнение дополнительного запроса для каждой пары
        #   algorithm_name, day
        for algorithm_name, day, daily_total, cnt in aggregated_results:
            cursor.execute('''
            SELECT type, total FROM deals
            WHERE algorithm_name = ? AND date(SUBSTR(datetime, 1, 19)) = date(?)
            ORDER BY datetime DESC
            LIMIT 1
            ''', (algorithm_name, day))

            last_operation_type, last_total = cursor.fetchone()

            is_closed = last_operation_type == 2
            if is_closed:
                total = daily_total
            else:
                # Если тип последней операции равен 1, вычитаем её total из итогового результата
                total = daily_total - last_total

            results.append(HistoricalTradeDTO(
                day,
                algorithm_name,
                round(total, 2),
                cnt,
                is_closed,
            ))

        conn.close()

        return results

    def print_hourly_totals(self, date=None):
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')  # Текущая дата в формате строки

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Получаем данные за указанный день
        cursor.execute('''
        SELECT 
            algorithm_name,
            strftime('%H', SUBSTR(datetime, 1, 19)) AS hour,
            total,
            type
        FROM deals
        WHERE date(SUBSTR(datetime, 1, 19)) = ?
        ORDER BY algorithm_name, hour, datetime, id
        ''', (date,))

        results = cursor.fetchall()

        # группировка по имени алгоритма
        for algorithm_name, algorithm_group in groupby(results, key=lambda x: x[0]):
            algorithm_list = list(algorithm_group)

            print(f"Algorithm: {algorithm_name}")

            sum_price = 0
            prev_show = None
            # группировка часам
            for hour, hour_group in groupby(algorithm_list, key=lambda x: x[1]):
                hour_list = list(hour_group)

                hour_sum_price = 0
                operation_type = 0
                operation_total = 0
                for _, _, operation_total, operation_type in hour_list:
                    hour_sum_price += operation_total

                sum_price += hour_sum_price

                show_sum = sum_price
                # откидываем последнюю операцию, но только для локального вывода
                if operation_type == 1:
                    show_sum -= operation_total
                    # diff -= operation_total

                print(f"  {hour}: {round(show_sum, 2)} "
                      f"({round(show_sum - prev_show, 2) if prev_show is not None else '0'})")

                prev_show = show_sum

        conn.close()

    def get_deals(self, date: str, algorithm_name: str) -> list[DealDTO]:
        db_file = self.db_file
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Форматируем дату для поиска в формате 'YYYY-MM-DD%'
        date_formatted = f"{date}%"

        # Выполняем запрос к базе данных
        cursor.execute("""
            SELECT id, datetime, type, algorithm_name, price, commission, total
            FROM deals
            WHERE datetime LIKE ? AND algorithm_name = ?
            ORDER BY datetime
        """, (date_formatted, algorithm_name))

        rows = cursor.fetchall()
        conn.close()

        # Преобразование результатов запроса в список объектов DealDTO
        deals = [DealDTO(row[0], row[1], row[2], row[3], row[4], row[5], row[6]) for row in rows]

        return deals
