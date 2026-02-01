import pandas as pd
import yfinance as yf
import requests
import io
import os

DATA_PATH = 'data/'

# Запасной список тикеров на случай, если Википедия недоступна
FALLBACK_TICKERS = [
    "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "TSLA", "META", "BRK-B", "UNH", "JNJ",
    "XOM", "V", "PG", "JPM", "MA", "HD", "CVX", "LLY", "ABBV", "PEP",
    "KO", "MRK", "BAC", "AVGO", "TMO", "COST", "CSCO", "MCD", "WMT", "ADBE",
    "PFE", "DIS", "ACN", "ABT", "DHR", "NFLX", "LIN", "NKE", "TXN", "NEE"
]

def load_real_data():
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    
    print("--- ЗАГРУЗКА ДАННЫХ (ROBUST VERSION) ---")

    # 1. Получаем список тикеров
    print("\n1. Получение списка компаний...")
    tickers_list = []
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        s = requests.get(url, headers=headers).content
        table = pd.read_html(io.BytesIO(s))
        sp500_df = table[0]
        sp500_df['Symbol'] = sp500_df['Symbol'].str.replace('.', '-', regex=False)
        tickers_list = sp500_df['Symbol'].tolist()
        print(f"   Успех: Найдено {len(tickers_list)} компаний на Википедии.")
    except Exception as e:
        print(f"   ПРЕДУПРЕЖДЕНИЕ: Не удалось скачать с Википедии ({e}).")
        print("   Использую запасной список (Top 40).")
        tickers_list = FALLBACK_TICKERS

    if not tickers_list:
        tickers_list = FALLBACK_TICKERS

    # 2. Скачивание БЕНЧМАРКА (^GSPC)
    print("\n2. Скачивание индекса S&P 500 (^GSPC)...")
    try:
        # period="5y" надежнее дат в некоторых версиях
        sp500_index = yf.download("^GSPC", period="5y", interval="1d", auto_adjust=True, progress=False)
        
        if sp500_index.empty:
            print("   ОШИБКА: Индекс пуст. Пробую другой метод...")
            sp500_index = yf.Ticker("^GSPC").history(period="5y")
        
        sp500_index = sp500_index.reset_index()
        sp500_index.columns = sp500_index.columns.str.lower()
        
        # Исправление часовых поясов (удаляем tz info)
        if 'date' in sp500_index.columns:
            sp500_index['date'] = sp500_index['date'].dt.tz_localize(None)
        
        sp500_path = os.path.join(DATA_PATH, 'sp500.csv')
        sp500_index.to_csv(sp500_path, index=False)
        print(f"   Бенчмарк сохранен: {len(sp500_index)} строк.")
        
    except Exception as e:
        print(f"   КРИТИЧЕСКАЯ ОШИБКА скачивания индекса: {e}")

    # 3. Скачивание АКЦИЙ
    print(f"\n3. Скачивание цен для {len(tickers_list)} компаний...")
    try:
        # Скачиваем пакетом
        data = yf.download(
            tickers_list, 
            period="5y", 
            interval="1d",
            auto_adjust=True,
            threads=True,
            progress=True
        )
        
        if data.empty:
            print("   ОШИБКА: yfinance вернул пустой DataFrame!")
            return

        # Извлечение Close
        if 'Close' in data.columns.levels[0]:
            close_prices = data['Close']
        else:
            # Если скачалось без мультииндекса (редко для списка)
            close_prices = data['Close'] if 'Close' in data.columns else data

        # Форматирование
        stacked = close_prices.stack()
        prices_df = stacked.reset_index()
        prices_df.columns = ['date', 'ticker', 'price']
        
        # Удаляем таймзону у дат
        prices_df['date'] = pd.to_datetime(prices_df['date']).dt.tz_localize(None)
        
        prices_df = prices_df.sort_values(by=['date', 'ticker'])
        
        # Проверка на пустоту
        if len(prices_df) == 0:
            print("   ОШИБКА: После обработки данных осталось 0 строк.")
            return

        prices_path = os.path.join(DATA_PATH, 'stock_prices.csv')
        prices_df.to_csv(prices_path, index=False)
        print(f"   УСПЕХ! Сохранено {len(prices_df)} строк цен.")

    except Exception as e:
        print(f"   КРИТИЧЕСКАЯ ОШИБКА скачивания акций: {e}")

if __name__ == "__main__":
    load_real_data()