import sqlite3
from datetime import datetime, timedelta, timezone
from tinkoff.invest import Client, GetCandlesResponse, CandleInterval, Quotation, HistoricCandle


class HistoricalCandles:
    def __init__(self, token, figi, ticker):
        self.token = token
        self.figi = figi
        self.ticker = ticker
        self.db_file = f"./db/test_{ticker}.db"
        self.create_database()

    def create_database(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candles (
            date DATETIME PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER
        )
        ''')
        conn.commit()
        conn.close()

    def clear_candles_table(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM candles WHERE 1')
        conn.commit()
        conn.close()

    @staticmethod
    def get_days_list(end_date, days_num):
        """
        Возвращает список предыдущих будних дней.

        :param end_date: Строка с датой в формате "YYYY-MM-DD".
        :param days_num: Число дней для возврата.
        :return: Список строк с датами предыдущих будних дней.
        """
        weekdays = []
        current_date = datetime.strptime(end_date, "%Y-%m-%d")

        while len(weekdays) < days_num:
            # Проверяем, является ли день будним (понедельник=0, воскресенье=6)
            if current_date.weekday() < 5:  # Понедельник=0, вторник=1, ..., пятница=4
                # Добавляем дату в список, если это будний день
                weekdays.append(current_date.strftime("%Y-%m-%d"))

            # Вычитаем один день для проверки следующего дня
            current_date -= timedelta(days=1)

        weekdays.reverse()

        return weekdays

    @staticmethod
    def get_hour_minute_pairs(start_datetime, end_datetime):
        """итератор по минутам для заданного времени"""
        current_datetime = start_datetime
        while current_datetime <= end_datetime:
            yield current_datetime
            current_datetime += timedelta(minutes=1)

    @staticmethod
    def q2f(quotation: Quotation, digits=2):
        return round(quotation.units + quotation.nano * 1e-9, digits)

    @staticmethod
    def f2q(value):
        units = int(value)
        nano = int(round(value - units, 2) * 1e9)
        return Quotation(units=units, nano=nano)

    def get_candles(self, date):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if date == today:
            # Запрос к API для сегодняшней даты
            return self.fetch_candles_from_api(date)

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM candles WHERE date(date) = ?', (date,))
        rows = cursor.fetchall()
        conn.close()

        if rows and len(rows) > 1:
            candles = []
            for row in rows:
                date, open_, high, low, close, volume = row
                candle = HistoricCandle(
                    time=datetime.strptime(date, "%Y-%m-%d %H:%M:%S+00:00"),
                    open=self.f2q(open_),
                    high=self.f2q(high),
                    low=self.f2q(low),
                    close=self.f2q(close),
                    volume=volume,
                    is_complete=True
                )
                candles.append(candle)
            return GetCandlesResponse(candles=candles)
        else:
            # Запрос к API, если нет данных в базе
            return self.fetch_candles_from_api(date)

    def fetch_candles_from_api(self, date):
        with Client(self.token) as client:
            from_time = datetime.strptime(date + " 06:55", "%Y-%m-%d %H:%M")
            to_time = datetime.strptime(date + " 19:00", "%Y-%m-%d %H:%M")
            candles = client.market_data.get_candles(
                figi=self.figi,
                from_=from_time,
                to=to_time,
                interval=CandleInterval.CANDLE_INTERVAL_1_MIN
            )
            return candles
