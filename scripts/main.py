import sys
from pathlib import Path
import pandas as pd
import os

# Добавляем путь для импортов
sys.path.append(str(Path(__file__).parent))

from memory_reducer import reduce_memory_usage
from preprocessing import preprocessing
from create_signal import create_signal
from backtester import backtest

# Пути
BASE_DIR = Path("data")
PRICES_PATH = BASE_DIR / "stock_prices.csv"
SP500_PATH = BASE_DIR / "sp500.csv"
RESULTS_DIR = Path("results")

def main():
    print("=== Starting Project: Backtesting S&P 500 ===")

    if not PRICES_PATH.exists() or not SP500_PATH.exists():
        print("Data not found. Please run 'python3 scripts/data_loader.py' first!")
        return

    # 1. Загрузка
    print("\n[1] Loading Data...")
    prices = pd.read_csv(PRICES_PATH)
    sp500 = pd.read_csv(SP500_PATH)
    
    print(f"DEBUG: Loaded {len(prices)} rows of price data.")

    # 2. Оптимизация памяти
    print("\n[2] Reducing Memory...")
    prices = reduce_memory_usage(prices)
    
    # ПРОВЕРКА: Не удалил ли редюсер данные?
    print(f"DEBUG: Rows after memory reducer: {len(prices)}")
    if len(prices) == 0:
        print("CRITICAL ERROR: Memory reducer destroyed the data!")
        return

    # 3. Препроцессинг
    print("\n[3] Preprocessing...")
    prices_clean, sp500_clean = preprocessing(prices, sp500, results_dir=RESULTS_DIR)

    if prices_clean.empty:
        print("CRITICAL ERROR: Preprocessing returned empty DataFrame.")
        return

    # 4. Генерация сигналов
    print("\n[4] Generating Signals...")
    prices_with_signal = create_signal(prices_clean)

    # 5. Бэктест
    print("\n[5] Backtesting...")
    backtest(prices_with_signal, sp500_clean, results_dir=RESULTS_DIR)

    print("\n=== Pipeline Completed Successfully ===")

if __name__ == "__main__":
    main()