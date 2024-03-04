from tinkoff.invest import Client
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("INVEST_TOKEN")
ACCOUNT_ID = os.getenv("ACCOUNT_ID")

# Функция для поиска FIGI по тикеру инструмента
def find_figi_by_ticker(ticker):
    with Client(TOKEN) as client:
        # Используем метод инструментов для поиска по тикеру
        instruments = client.instruments.shares()
        for instrument in instruments.instruments:
            if instrument.ticker == ticker:
                return instrument.figi
    return None

# Пример использования функции
ticker = "RNFT"  # Пример тикера
figi = find_figi_by_ticker(ticker)
if figi:
    print(f"FIGI для {ticker}:", figi)
else:
    print(f"Инструмент с тикером {ticker} не найден.")