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

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candles_day (
            date DATE PRIMARY KEY,
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
        out = []
        current_date = datetime.strptime(end_date, "%Y-%m-%d")

        while len(out) < days_num:
            out.append(current_date.strftime("%Y-%m-%d"))
            current_date -= timedelta(days=1)

        out.reverse()

        return out

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
            # Запрос к API для сегодняшней даты всегда к API и без сохранения
            return self.fetch_candles_from_api(date, False)

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM candles WHERE date(date) = ?', (date,))
        rows = cursor.fetchall()
        conn.close()

        if rows:
            if len(rows) == 1:
                return GetCandlesResponse(candles=[])

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
            return self.fetch_candles_from_api(date, True)

    def fetch_candles_from_api(self, date, save=True):
        with Client(self.token) as client:
            from_time = datetime.strptime(date + " 06:55", "%Y-%m-%d %H:%M")
            to_time = datetime.strptime(date + " 19:00", "%Y-%m-%d %H:%M")
            candles = client.market_data.get_candles(
                figi=self.figi,
                from_=from_time,
                to=to_time,
                interval=CandleInterval.CANDLE_INTERVAL_1_MIN
            )

            if save:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()

                if candles.candles:
                    for candle in candles.candles:
                        cursor.execute('''
                        INSERT OR IGNORE INTO candles (date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            candle.time,
                            self.q2f(candle.open),
                            self.q2f(candle.high),
                            self.q2f(candle.low),
                            self.q2f(candle.close),
                            candle.volume
                        ))
                    conn.commit()

                else:
                    # Сохранение записи-признака отсутствия данных
                    cursor.execute('''
                    INSERT OR IGNORE INTO candles (date, open, high, low, close, volume)
                    VALUES (?, 0, 0, 0, 0, 0)
                    ''', (date + " 00:00",))
                    conn.commit()

                conn.close()

            return candles

    def get_day_candles(self, from_date, to_date) -> GetCandlesResponse:
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        dates_needed = [from_date + timedelta(days=x) for x in range((to_date - from_date).days + 1)]
        candles = []

        for date_needed in dates_needed:
            cursor.execute('SELECT * FROM candles_day WHERE date = ?', (date_needed.strftime('%Y-%m-%d'),))
            row = cursor.fetchone()
            if row:
                date, open_, high, low, close, volume = row
                if open_ > 0:
                    candle = HistoricCandle(
                        time=datetime.strptime(date, "%Y-%m-%d"),
                        open=self.f2q(open_),
                        high=self.f2q(high),
                        low=self.f2q(low),
                        close=self.f2q(close),
                        volume=volume,
                        is_complete=True
                    )
                    candles.append(candle)
            else:
                # Если данных нет в базе, запросить из API и сохранить
                with Client(self.token) as client:
                    api_candles = client.market_data.get_candles(
                        figi=self.figi,
                        from_=date_needed.replace(hour=0, minute=0, second=0),
                        to=date_needed.replace(hour=23, minute=59, second=59),
                        interval=CandleInterval.CANDLE_INTERVAL_DAY
                    )
                    if api_candles.candles:
                        for candle in api_candles.candles:
                            candles.append(candle)
                            cursor.execute(
                                'INSERT OR IGNORE INTO candles_day (date, open, high, low, close, volume) '
                                'VALUES (?, ?, ?, ?, ?, ?)',
                                (
                                    candle.time.date(),
                                    self.q2f(candle.open),
                                    self.q2f(candle.high),
                                    self.q2f(candle.low),
                                    self.q2f(candle.close),
                                    candle.volume
                                ))
                            conn.commit()

                    # хак. если в эту дату нет данных, то возвращается предыдущая и в нужную не пишется ничего
                    cursor.execute('''
                    INSERT OR IGNORE INTO candles_day (date, open, high, low, close, volume)
                    VALUES (?, 0, 0, 0, 0, 0)
                    ''', (date_needed.date(),))
                    conn.commit()

        conn.close()
        return GetCandlesResponse(candles=candles)
