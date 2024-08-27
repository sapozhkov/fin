import sqlite3
from datetime import datetime, timedelta

from tinkoff.invest import GetCandlesResponse, HistoricCandle, Client, CandleInterval

from bot.dto import InstrumentDTO
from app.config import AppConfig
from app.helper import TimeHelper, q2f, f2q, LocalCache


class TickerCache:
    def __init__(self, ticker):
        self.token = AppConfig.TOKEN
        self.ticker = ticker
        self.db_file = f"{AppConfig.BASE_DIR}/db/c_{ticker}.db"
        self.create_database()
        self.instrument: InstrumentDTO | None = None
        self.cache = {}

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

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS instrument (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL 
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

    def clear_instrument_table(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM instrument WHERE 1')
        conn.commit()
        conn.close()

    @staticmethod
    def get_days_list(end_date, days_num):
        """
        Возвращает список предыдущих будних дней.

        :param end_date: Строка с датой в формате "YYYY-MM-DD".
        :param days_num: Число дней для возврата.
        :return: Список строк с датами предыдущих дней.
        """
        out = []
        current_date = datetime.strptime(end_date, "%Y-%m-%d")

        while len(out) < days_num:
            out.append(current_date.strftime("%Y-%m-%d"))
            current_date -= timedelta(days=1)

        out.reverse()

        return out

    @staticmethod
    def get_days_list_working_only(end_date, days_num):
        """
        Возвращает список предыдущих будних дней, но только рабочих

        :param end_date: Строка с датой в формате "YYYY-MM-DD".
        :param days_num: Число дней для возврата.
        :return: Список строк с датами предыдущих будних дней.
        """
        current_date = datetime.strptime(end_date, "%Y-%m-%d")
        out = [end_date]

        while len(out) < days_num:
            current_date -= timedelta(days=1)
            if TimeHelper.is_working_day(current_date):
                out.append(current_date.strftime("%Y-%m-%d"))

        out.reverse()

        return out

    def get_candles(self, date, force_cache=False):
        if TimeHelper.is_today(date):
            # Запрос к API для сегодняшней даты всегда к API и без сохранения, если нет принудительного флага
            return self.fetch_candles_from_api(date, force_cache)

        cache_key = f"candle_{self.ticker}_{date}"
        cache_val = LocalCache.get(cache_key)

        if cache_val is not None:
            return cache_val

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM candles WHERE date(date) = ?', (date,))
        rows = cursor.fetchall()
        conn.close()

        if rows:
            if len(rows) == 1:
                val = GetCandlesResponse(candles=[])
                LocalCache.set(cache_key, val)
                return val

            candles = []
            for row in rows:
                date, open_, high, low, close, volume = row
                try:
                    candle = HistoricCandle(
                        time=datetime.strptime(date, "%Y-%m-%d %H:%M:%S+00:00"),
                        open=f2q(open_),
                        high=f2q(high),
                        low=f2q(low),
                        close=f2q(close),
                        volume=volume,
                        is_complete=True
                    )
                    candles.append(candle)
                except ValueError:
                    pass
            val = GetCandlesResponse(candles=candles)
            LocalCache.set(cache_key, val)
            return val
        else:
            # Запрос к API, если нет данных в базе
            return self.fetch_candles_from_api(date, True)

    def fetch_candles_from_api(self, date, save=True):
        with Client(self.token) as client:
            from_time = datetime.strptime(date + " 06:55", "%Y-%m-%d %H:%M")
            to_time = datetime.strptime(date + " 19:00", "%Y-%m-%d %H:%M")
            candles = client.market_data.get_candles(
                figi=self.get_instrument().figi,
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
                            q2f(candle.open),
                            q2f(candle.high),
                            q2f(candle.low),
                            q2f(candle.close),
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

        # запрашиваем из базы все, что есть по этим датам
        cursor.execute(
            'SELECT * FROM candles_day WHERE date >= ? AND date <= ?',
            (from_date.strftime('%Y-%m-%d'), to_date.strftime('%Y-%m-%d')))
        data_dict = dict([(row[0], row) for row in cursor.fetchall()])

        for date_needed in dates_needed:
            _date = date_needed.strftime('%Y-%m-%d')
            is_today = TimeHelper.is_today(_date)
            if _date in data_dict:
                date, open_, high, low, close, volume = data_dict[_date]
                if open_ > 0:
                    candle = HistoricCandle(
                        time=datetime.strptime(date, "%Y-%m-%d"),
                        open=f2q(open_),
                        high=f2q(high),
                        low=f2q(low),
                        close=f2q(close),
                        volume=volume,
                        is_complete=True
                    )
                    candles.append(candle)
            else:
                # Если данных нет в базе, запросить из API и сохранить
                with Client(self.token) as client:
                    api_candles = client.market_data.get_candles(
                        figi=self.get_instrument().figi,
                        from_=date_needed.replace(hour=0, minute=0, second=0),
                        to=date_needed.replace(hour=23, minute=59, second=59),
                        interval=CandleInterval.CANDLE_INTERVAL_DAY
                    )
                    if api_candles.candles:
                        for candle in api_candles.candles:
                            candles.append(candle)
                            # сегодняшний день в базу не заносим - меняется до конца дня
                            if not is_today:
                                cursor.execute(
                                    'INSERT OR IGNORE INTO candles_day (date, open, high, low, close, volume) '
                                    'VALUES (?, ?, ?, ?, ?, ?)',
                                    (
                                        candle.time.date(),
                                        q2f(candle.open),
                                        q2f(candle.high),
                                        q2f(candle.low),
                                        q2f(candle.close),
                                        candle.volume
                                    ))
                                conn.commit()

                    if not is_today:
                        # хак. если в эту дату нет данных, то возвращается предыдущая и в нужную не пишется ничего
                        cursor.execute('''
                        INSERT OR IGNORE INTO candles_day (date, open, high, low, close, volume)
                        VALUES (?, 0, 0, 0, 0, 0)
                        ''', (date_needed.date(),))
                        conn.commit()

        conn.close()
        return GetCandlesResponse(candles=candles)

    def get_instrument(self) -> InstrumentDTO:
        if self.instrument:
            return self.instrument

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Выбираем все данные из таблицы
        cursor.execute("SELECT key, value FROM instrument")
        rows = cursor.fetchall()
        data_dict = {}
        for key, val in rows:
            data_dict[key] = val

        instrument_fields = vars(InstrumentDTO())

        # если нет - запрашиваем из API
        if len(data_dict) != len(instrument_fields):
            self.clear_instrument_table()

            with Client(self.token) as client:
                instruments = client.instruments.shares()
                for instrument in instruments.instruments:
                    if instrument.ticker == self.ticker:
                        min_increment = instrument.min_price_increment.units + \
                                        instrument.min_price_increment.nano * 1e-9
                        min_increment_str = str(min_increment)
                        decimal_point_index = min_increment_str.find('.')
                        if decimal_point_index == -1:
                            round_signs = 0
                        else:
                            round_signs = len(min_increment_str) - decimal_point_index - 1
                        min_increment = round(min_increment, round_signs)

                        data_dict = {
                            'ticker': self.ticker,
                            'figi': instrument.figi,
                            'name': instrument.name,
                            'currency': instrument.currency,
                            'round_signs': round_signs,
                            'min_increment': min_increment,
                            'lot': instrument.lot,
                            'short_enabled_flag': instrument.short_enabled_flag,
                        }

            # кладем в таблицу
            for key, val in data_dict.items():
                # Добавляем строку в таблицу
                cursor.execute("INSERT OR IGNORE INTO instrument (key, value) VALUES (?, ?)",
                               (key, val))

            # Сохраняем изменения
            conn.commit()

        # Закрываем соединение с базой данных
        conn.close()

        if len(data_dict) == 0:
            raise Exception(f"No figi found for '{self.ticker}'")

        # отдаем объект
        self.instrument = InstrumentDTO(**data_dict)
        return self.instrument
