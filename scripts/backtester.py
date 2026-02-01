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
    signal = prices["signal"].fillna(0).astype(int)
    
    # Доход по каждой акции: будущая доходность * сигнал * размер инвестиции.
    pnl = prices["monthly_future_return"] * signal * INVESTMENT_PER_STOCK
    
    # Агрегируем по месяцам (уровень индекса 'date').
    monthly_pnl = pnl.groupby(level="date").sum()
    monthly_signal = signal.groupby(level="date").sum()
    
    # Доходность месяца: суммарный PnL на количество выбранных акций.
    # Защита от деления на ноль, если сигналов не было
    monthly_return = monthly_pnl.divide(monthly_signal).fillna(0.0)
    
    return monthly_pnl, monthly_return, monthly_signal


def _save_results(text: str, output_path: Path) -> None:
    """Сохранить текстовый отчет в файл."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def backtest(prices: pd.DataFrame, sp500: pd.DataFrame, results_dir: str | Path = "results") -> Tuple[pd.Series, pd.Series]:
    """Запустить бэктест стратегии и сравнить ее с S&P 500."""
    print("--- Running Backtest ---")
    results_path = Path(results_dir)

    # 1. Стратегия: считаем метрики
    strat_monthly_pnl, strat_monthly_return, strat_monthly_signal = _strategy_monthly_pnl(prices)
    strat_cum_pnl = strat_monthly_pnl.cumsum()

    # --- ЗАЩИТА ОТ КРАША (Fix for IndexError) ---
    if strat_cum_pnl.empty:
        print("CRITICAL WARNING: No trades generated. Cannot calculate performance.")
        return pd.Series(), pd.Series()

    strat_total_pnl = strat_cum_pnl.iloc[-1]
    
    # Защита от деления на ноль в итоговом расчете
    total_signals = strat_monthly_signal.sum()
    strat_total_return = strat_total_pnl / total_signals if total_signals > 0 else 0.0

    # 2. Бенчмарк: моделируем те же 20 акций как инвестицию в индекс
    # Выравниваем индекс бенчмарка по датам стратегии (inner join логика)
    sp500_aligned = sp500.loc[sp500.index.intersection(strat_cum_pnl.index)]
    
    if sp500_aligned.empty:
        print("WARNING: Benchmark dates do not match Strategy dates.")
        sp_total_pnl = 0.0
        sp_total_return = 0.0
        sp_cum_pnl = pd.Series()
    else:
        sp_signal = pd.Series(STOCKS_PER_MONTH, index=sp500_aligned.index, name="signal")
        sp_monthly_pnl = sp_signal * sp500_aligned["monthly_return"] * INVESTMENT_PER_STOCK
        sp_monthly_return = sp_monthly_pnl / sp_signal
        sp_cum_pnl = sp_monthly_pnl.cumsum()
        sp_total_pnl = sp_cum_pnl.iloc[-1]
        sp_total_return = sp_total_pnl / sp_signal.sum()

    # 3. Сохраняем отчет
    results_text = (
        "Stock Picking 20:\n"
        f"  Total PnL: {strat_total_pnl:.2f}\n"
        f"  Total Return: {strat_total_return:.4f}\n\n"
        "S&P 500 Benchmark:\n"
        f"  Total PnL: {sp_total_pnl:.2f}\n"
        f"  Total Return: {sp_total_return:.4f}\n"
    )
    _save_results(results_text, results_path / "results.txt")
    print(f"Backtest Finished. Strategy PnL: {strat_total_pnl:.2f}")

    # 4. График
    plot_path = results_path / "plots" / "strategy_vs_sp500.png"
    plot_path.parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 6))
    if not strat_cum_pnl.empty:
        plt.plot(strat_cum_pnl.index, strat_cum_pnl.values, label="Stock Picking 20")
    if not sp_cum_pnl.empty:
        plt.plot(sp_cum_pnl.index, sp_cum_pnl.values, label="S&P 500", linestyle="--")
        
    plt.title("Cumulative PnL: Strategy vs S&P 500")
    plt.xlabel("Date")
    plt.ylabel("Cumulative PnL ($)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()

    return strat_cum_pnl, sp_cum_pnl