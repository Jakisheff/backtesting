"""Построение сигнала отбора акций на основе прошлых доходностей."""

from __future__ import annotations
import pandas as pd
import numpy as np

def create_signal(prices: pd.DataFrame) -> pd.DataFrame:
    """Добавить в таблицу колонку сигнала для топ-20 акций по доходности."""
    print("--- Creating Signals (Debug Mode) ---")
    
    # 0. Проверка на входе
    if prices.empty:
        print("ERROR: Input DataFrame is empty!")
        return prices
    
    # Работаем с копией
    df = prices.copy()
    
    # 1. СБРОС ИНДЕКСА (Reset Index)
    # Это гарантирует, что 'ticker' и 'date' станут обычными колонками.
    # Так мы избежим любых проблем с MultiIndex.
    if isinstance(df.index, pd.MultiIndex):
        df = df.reset_index()
    
    print(f"DEBUG: Data shape: {df.shape}")
    print(f"DEBUG: Columns: {df.columns.tolist()}")
    
    # Убеждаемся, что сортировка правильная
    df = df.sort_values(by=['ticker', 'date'])

    # 2. Расчет средней доходности (12 месяцев)
    # Используем transform по колонке 'ticker'
    print("DEBUG: Calculating 12-month rolling mean...")
    df["average_return_1y"] = df.groupby("ticker")["monthly_past_return"].transform(
        lambda x: x.rolling(window=12, min_periods=12).mean()
    )

    # Статистика по метрике
    valid_metrics = df["average_return_1y"].notna().sum()
    print(f"DEBUG: Rows with valid 1Y return: {valid_metrics}")
    
    if valid_metrics == 0:
        print("CRITICAL WARNING: No valid 1Y returns calculated.")
        print("Possible reasons: History too short (<12 months) or gaps in data.")
        # Возвращаем структуру обратно в MultiIndex перед выходом
        if 'date' in df.columns and 'ticker' in df.columns:
            return df.set_index(['date', 'ticker']).sort_index()
        return df

    # 3. Ранжирование
    # Берем только строки с валидной метрикой
    valid_mask = df["average_return_1y"].notna()
    
    # Ранжируем внутри каждой даты
    df.loc[valid_mask, "rank"] = df.loc[valid_mask].groupby("date")["average_return_1y"].rank(
        method="first", ascending=False
    )
    
    # 4. Сигнал (Топ 20)
    df["signal"] = 0
    df.loc[df["rank"] <= 20, "signal"] = 1
    
    total_signals = df["signal"].sum()
    print(f"DEBUG: Total trades generated: {total_signals}")

    # 5. ВОЗВРАТ ИНДЕКСА (Restore Index)
    # Backtester ожидает индекс (date, ticker) или хотя бы date
    # Возвращаем к формату (date, ticker)
    df = df.set_index(['date', 'ticker']).sort_index()
    
    return df