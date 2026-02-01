"""Предобработка цен акций и индекса S&P 500 для дальнейшего анализа. (DEBUG VERSION)"""

from __future__ import annotations
from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Константы
PRICE_MIN = 0.1
PRICE_MAX = 10000

def _monthly_last(df: pd.DataFrame) -> pd.DataFrame:
    """Перевести данные на месячную частоту."""
    return df.resample("M").last()

def _reshape_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Преобразовать цены из wide-формата в long-формат с индексом (date, ticker)."""
    prices = prices.copy()
    print(f"DEBUG: _reshape_prices input shape: {prices.shape}")
    
    # 1. Приводим дату к формату
    if "date" in prices.columns:
        prices["date"] = pd.to_datetime(prices["date"], errors='coerce')
    elif "Date" in prices.columns:
         prices["Date"] = pd.to_datetime(prices["Date"], errors='coerce')
         prices = prices.rename(columns={"Date": "date"})
    
    # Удаляем строки с невалидной датой
    prices = prices.dropna(subset=['date'])
    print(f"DEBUG: Rows after date conversion: {len(prices)}")

    # 2. PIVOT
    # Удаляем дубликаты перед пивотом
    prices = prices.drop_duplicates(subset=["date", "ticker"], keep="last")
    try:
        prices_wide = prices.pivot(index="date", columns="ticker", values="price")
        print(f"DEBUG: Pivot successful. Wide shape: {prices_wide.shape}")
    except Exception as e:
        print(f"DEBUG ERROR: Pivot failed: {e}")
        return pd.DataFrame()

    # 3. Resample
    prices_monthly = _monthly_last(prices_wide)
    print(f"DEBUG: Rows after resampling (Months): {len(prices_monthly)}")

    # 4. Stack
    try:
        stacked = prices_monthly.stack(future_stack=True)
    except TypeError:
        stacked = prices_monthly.stack()
    
    prices_long = stacked.to_frame("price").rename_axis(index=["date", "ticker"])
    
    print(f"DEBUG: Reshaped long format shape: {prices_long.shape}")
    return prices_long.sort_index()

def _filter_price_range(prices_long: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Заменить нереалистичные цены на NaN и вернуть найденные выбросы."""
    prices_long = prices_long.copy()
    mask = (prices_long["price"] < PRICE_MIN) | (prices_long["price"] > PRICE_MAX)
    
    # Сохраняем выбросы для отчета
    price_outliers = prices_long[mask].copy().reset_index()
    
    prices_long.loc[mask, "price"] = np.nan
    
    valid_count = prices_long['price'].notna().sum()
    print(f"DEBUG: Valid prices ($0.1 - $10k): {valid_count} (out of {len(prices_long)})")
    print(f"DEBUG: Price outliers detected: {len(price_outliers)}")
    return prices_long, price_outliers

def _compute_returns(prices_long: pd.DataFrame) -> pd.DataFrame:
    """Добавить доходности."""
    prices_long = prices_long.copy()
    grouped = prices_long.groupby("ticker")
    
    # pct_change
    prices_long["monthly_past_return"] = grouped["price"].pct_change(fill_method=None)
    
    # future return
    future_price = grouped["price"].shift(-1)
    prices_long["monthly_future_return"] = future_price / prices_long["price"] - 1
    
    # Проверка, сколько рассчиталось
    valid_returns = prices_long["monthly_past_return"].notna().sum()
    print(f"DEBUG: Rows with valid calculated returns: {valid_returns}")
    return prices_long

def _replace_outlier_returns(prices_long: pd.DataFrame) -> pd.DataFrame:
    """Заменить выбросы."""
    prices_long = prices_long.copy()
    dates = prices_long.index.get_level_values("date")
    in_crisis = dates.year.isin([2008, 2009])

    for col in ["monthly_past_return", "monthly_future_return"]:
        outliers = (prices_long[col] > 1.0) | (prices_long[col] < -0.5)
        mask = outliers & (~in_crisis)
        prices_long.loc[mask, col] = np.nan
    
    return prices_long

def _fill_missing(prices_long: pd.DataFrame) -> pd.DataFrame:
    """Заполнить пропуски и удалить NaN."""
    prices_long = prices_long.copy()
    
    # Ffill
    prices_long["price"] = prices_long.groupby("ticker")["price"].ffill()
    prices_long["monthly_past_return"] = prices_long.groupby("ticker")["monthly_past_return"].ffill()
    
    # DROPNA - Самое опасное место
    before_drop = len(prices_long)
    prices_long = prices_long.dropna()
    after_drop = len(prices_long)
    
    print(f"DEBUG: _fill_missing dropna: {before_drop} -> {after_drop} rows")
    return prices_long

def _detect_outliers(prices_long: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    """Найти первые выбросы."""
    returns = prices_long[["price", "monthly_past_return"]].copy()
    outliers = (returns["monthly_past_return"] > 1) | (returns["monthly_past_return"] < -0.5)
    return returns[outliers].reset_index().sort_values("date").head(limit)

def _save_outliers(outliers: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["ticker,date,price,return"]
    for _, row in outliers.iterrows():
        lines.append(f"{row['ticker']},{row['date'].date()},{row['price']},{row.get('monthly_past_return', 'N/A')}")
    output_path.write_text("\n".join(lines), encoding="utf-8")

def plot_average_price(prices_long: pd.DataFrame, results_dir: Path, plot: bool = False):
    if prices_long.empty:
        return
    avg_price = prices_long.groupby(level="date")["price"].mean()
    plot_path = results_dir / "plots" / "avg_price.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(10, 5))
    plt.plot(avg_price.index, avg_price.values)
    plt.title("Average Stock Price Over Time")
    plt.xlabel("Date")
    plt.ylabel("Average Price")
    plt.tight_layout()
    plt.savefig(plot_path)
    if plot: return fig
    plt.close(fig)

def preprocess_prices(prices: pd.DataFrame, results_dir: Path) -> pd.DataFrame:
    """Пайплайн обработки цен."""
    print("DEBUG: Starting preprocess_prices...")
    prices_long = _reshape_prices(prices)
    if prices_long.empty: return prices_long
    
    prices_long, price_outliers = _filter_price_range(prices_long)
    prices_long = _compute_returns(prices_long)

    return_outliers = _detect_outliers(prices_long)
    
    # Объединяем выбросы по цене и по доходности
    all_outliers = pd.concat([price_outliers, return_outliers]).sort_values("date").head(5)
    
    _save_outliers(all_outliers, results_dir / "outliers.txt")
    plot_average_price(prices_long, results_dir, plot=False)

    prices_long = _replace_outlier_returns(prices_long)
    prices_long = _fill_missing(prices_long)

    print(f"DEBUG: Final clean prices shape: {prices_long.shape}")
    return prices_long

def preprocess_sp500(sp500: pd.DataFrame) -> pd.DataFrame:
    """Обработка бенчмарка."""
    sp500 = sp500.copy()
    if "date" in sp500.columns:
         sp500["date"] = pd.to_datetime(sp500["date"])
         sp500 = sp500.set_index("date").sort_index()
    elif "Date" in sp500.columns:
         sp500["Date"] = pd.to_datetime(sp500["Date"])
         sp500 = sp500.set_index("Date").sort_index()

    sp500 = _monthly_last(sp500)
    col_map = {c.lower(): c for c in sp500.columns}
    target_col = col_map.get("adjusted close") or col_map.get("close")
    
    if target_col:
        sp500["monthly_return"] = sp500[target_col].pct_change()
        sp500 = sp500.dropna()
    else:
        print("Warning: Close price column not found in SP500")
        
    return sp500

def preprocessing(prices: pd.DataFrame, sp500: pd.DataFrame, results_dir: str | Path = "results") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Точка входа."""
    print("--- Preprocessing Started ---")
    results_path = Path(results_dir)
    
    prices.columns = prices.columns.str.lower()
    sp500.columns = sp500.columns.str.lower()
    
    prices_clean = preprocess_prices(prices, results_path)
    sp500_clean = preprocess_sp500(sp500)
    
    print("--- Preprocessing Completed ---")
    return prices_clean, sp500_clean