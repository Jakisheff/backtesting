"""Точка входа пайплайна: загрузка, предобработка, сигнал и бэктест."""

from __future__ import annotations

from pathlib import Path

from memory_reducer import memory_reducer
from preprocessing import preprocessing
from create_signal import create_signal
from backtester import backtest


def main() -> None:
    """Запустить полный пайплайн анализа и бэктеста."""
    # Определяем корневую папку проекта.
    root = Path(__file__).resolve().parents[1]
    # Собираем пути к данным и папке результатов.
    data_dir = root / "data"
    results_dir = root / "results"

    # Карта путей для загрузки CSV.
    paths = {
        "prices": data_dir / "stock_prices.csv",
        "sp500": data_dir / "sp500.csv",
    }

    # 1) Загружаем данные с оптимизацией памяти.
    prices, sp500 = memory_reducer(paths)
    # 2) Чистим цены и индекс, сохраняем артефакты.
    prices, sp500 = preprocessing(prices, sp500, results_dir=results_dir)
    # 3) Строим сигнал отбора акций.
    prices = create_signal(prices)
    # 4) Запускаем бэктест и строим итоговые графики.
    backtest(prices, sp500, results_dir=results_dir)


if __name__ == "__main__":
    main()
