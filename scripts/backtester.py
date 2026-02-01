"""Бэктест стратегии и сравнение с индексом S&P 500."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd
import matplotlib.pyplot as plt


INVESTMENT_PER_STOCK = 1
STOCKS_PER_MONTH = 20


def _strategy_monthly_pnl(prices: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Посчитать месячную прибыль/доходность стратегии и число выбранных акций."""
    # Приводим сигнал к 0/1 для расчетов PnL.
    signal = prices["signal"].astype(int)
    # Доход по каждой акции: будущая доходность * сигнал * размер инвестиции.
    pnl = prices["monthly_future_return"] * signal * INVESTMENT_PER_STOCK
    # Агрегируем по месяцам.
    monthly_pnl = pnl.groupby(level="date").sum()
    monthly_signal = signal.groupby(level="date").sum()
    # Доходность месяца: суммарный PnL на количество выбранных акций.
    monthly_return = monthly_pnl / monthly_signal
    return monthly_pnl, monthly_return, monthly_signal


def _save_results(text: str, output_path: Path) -> None:
    """Сохранить текстовый отчет в файл."""
    # Создаем директорию результатов при необходимости.
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def backtest(prices: pd.DataFrame, sp500: pd.DataFrame, results_dir: str | Path = "results") -> Tuple[pd.Series, pd.Series]:
    """Запустить бэктест стратегии и сравнить ее с S&P 500."""
    results_path = Path(results_dir)

    # Стратегия: считаем месячные метрики и итоговые значения.
    strat_monthly_pnl, strat_monthly_return, strat_monthly_signal = _strategy_monthly_pnl(prices)
    strat_cum_pnl = strat_monthly_pnl.cumsum()
    strat_total_pnl = strat_cum_pnl.iloc[-1]
    strat_total_return = strat_total_pnl / strat_monthly_signal.sum()

    # Бенчмарк: моделируем те же 20 акций как инвестицию в индекс.
    sp_signal = pd.Series(STOCKS_PER_MONTH, index=sp500.index, name="signal")
    sp_monthly_pnl = sp_signal * sp500["monthly_return"] * INVESTMENT_PER_STOCK
    sp_monthly_return = sp_monthly_pnl / sp_signal
    sp_cum_pnl = sp_monthly_pnl.cumsum()
    sp_total_pnl = sp_cum_pnl.iloc[-1]
    sp_total_return = sp_total_pnl / sp_signal.sum()

    # Формируем и сохраняем текстовый отчет.
    results_text = (
        "Stock Picking 20:\n"
        f"  Total PnL: {strat_total_pnl:.2f}\n"
        f"  Total Return: {strat_total_return:.4f}\n\n"
        "S&P 500:\n"
        f"  Total PnL: {sp_total_pnl:.2f}\n"
        f"  Total Return: {sp_total_return:.4f}\n"
    )
    _save_results(results_text, results_path / "results.txt")

    # Строим и сохраняем график кумулятивного PnL.
    plot_path = results_path / "plots" / "strategy_vs_sp500.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.plot(strat_cum_pnl.index, strat_cum_pnl.values, label="Stock Picking 20")
    plt.plot(sp_cum_pnl.index, sp_cum_pnl.values, label="S&P 500")
    plt.title("Cumulative PnL: Strategy vs S&P 500")
    plt.xlabel("Date")
    plt.ylabel("Cumulative PnL")
    plt.legend()
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()

    return strat_cum_pnl, sp_cum_pnl
