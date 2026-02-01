"""Построение сигнала отбора акций на основе прошлых доходностей."""

from __future__ import annotations

import pandas as pd


def create_signal(prices: pd.DataFrame) -> pd.DataFrame:
    """Добавить в таблицу колонку сигнала для топ-20 акций по доходности."""
    # Работаем с копией, чтобы не мутировать входные данные.
    prices = prices.copy()
    # Рассчитываем среднюю месячную доходность за 12 месяцев по каждому тикеру.
    prices["average_return_1y"] = (
        prices.groupby("ticker")["monthly_past_return"]
        .rolling(12)
        .mean()
        .reset_index(level=0, drop=True)
    )

    # Внутри каждого месяца ранжируем акции и отмечаем топ-20 как сигнал.
    prices["signal"] = (
        prices.groupby(level="date")["average_return_1y"]
        .rank(method="first", ascending=False)
        .le(20)
    )

    return prices
