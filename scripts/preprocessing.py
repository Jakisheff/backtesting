"""Предобработка цен акций и индекса S&P 500 для дальнейшего анализа."""

from __future__ import annotations  # future-совместимость аннотаций типов

from pathlib import Path  # работа с путями
from typing import Tuple  # аннотации возвращаемых типов

import numpy as np  # численные операции и NaN
import pandas as pd  # табличные данные
import matplotlib.pyplot as plt  # графики


PRICE_MIN = 0.1  # нижняя граница допустимой цены
PRICE_MAX = 10000  # верхняя граница допустимой цены


def _monthly_last(df: pd.DataFrame) -> pd.DataFrame:
    """Перевести данные на месячную частоту, оставив последнее значение месяца."""
    # Переводим временной ряд на месячную частоту и берем последнее значение месяца.
    return df.resample("ME").last()  # ресемплинг по месяцам, берем last


def _reshape_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Преобразовать цены из wide-формата в long-формат с индексом (date, ticker)."""
    # Переводим wide-формат (тикеры в колонках) в long-формат (date, ticker).
    prices = prices.copy()  # не меняем исходный DataFrame
    prices = prices.set_index("Date").sort_index()  # Date в индекс + сортировка
    prices = _monthly_last(prices)  # переход на месячную частоту

    prices_long = (  # получаем long-формат
        prices.stack(future_stack=True)  # превращаем колонки-тикеры в индекс
        .to_frame("price")  # превращаем Series в DataFrame с колонкой price
        .rename_axis(index=["date", "ticker"])  # даем имена уровням индекса
    )

    return prices_long.sort_index()  # сортировка по (date, ticker)


def _filter_price_range(prices_long: pd.DataFrame) -> pd.DataFrame:
    """Заменить нереалистичные цены на NaN по заданным границам."""
    # Помечаем цены вне диапазона как пропуски.
    prices_long = prices_long.copy()  # не меняем исходный
    mask = (prices_long["price"] < PRICE_MIN) | (prices_long["price"] > PRICE_MAX)  # фильтр выбросов цены
    prices_long.loc[mask, "price"] = np.nan  # замена на NaN
    return prices_long  # возвращаем очищенные цены


def _compute_returns(prices_long: pd.DataFrame) -> pd.DataFrame:
    """Добавить прошлую и будущую месячную доходность по каждому тикеру."""
    # Считаем прошлую и будущую месячную доходность по каждому тикеру.
    prices_long = prices_long.copy()  # копия для безопасной модификации
    grouped = prices_long.groupby("ticker")  # группировка по тикеру
    prices_long["monthly_past_return"] = grouped["price"].pct_change(fill_method=None)  # доходность назад
    future_price = grouped["price"].shift(-1)  # цена следующего месяца
    prices_long["monthly_future_return"] = future_price / prices_long["price"] - 1  # доходность вперед
    return prices_long  # возвращаем с доходностями


def _replace_outlier_returns(prices_long: pd.DataFrame) -> pd.DataFrame:
    """Заменить выбросы доходности на NaN, кроме кризисных лет."""
    # Выбросы доходности: > 100% или < -50% (кроме кризисных лет).
    prices_long = prices_long.copy()  # копия
    dates = prices_long.index.get_level_values("date")  # уровень индекса date
    in_crisis = dates.year.isin([2008, 2009])  # маска кризисных лет

    for col in ["monthly_past_return", "monthly_future_return"]:
        outliers = (prices_long[col] > 1) | (prices_long[col] < -0.5)  # маска выбросов
        mask = outliers & (~in_crisis)  # не трогаем кризис
        prices_long.loc[mask, col] = np.nan  # заменяем выбросы на NaN

    return prices_long  # возвращаем без выбросов


def _fill_missing(prices_long: pd.DataFrame) -> pd.DataFrame:
    """Заполнить пропуски внутри тикера и убрать оставшиеся NaN."""
    # Заполняем пропуски внутри тикера (forward fill), затем убираем оставшиеся NaN.
    prices_long = prices_long.copy()  # копия
    prices_long["price"] = prices_long.groupby("ticker")["price"].ffill()  # протягиваем цену вперед
    prices_long["monthly_past_return"] = prices_long.groupby("ticker")["monthly_past_return"].ffill()  # протягиваем доходность
    prices_long = prices_long.dropna()  # удаляем строки, где NaN еще остались
    return prices_long  # возвращаем без пропусков


def _detect_outliers(prices_long: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    """Найти первые выбросы доходности для отчетности."""
    # Находим первые limit выбросов для отчета.
    returns = prices_long[["price", "monthly_past_return"]].copy()  # берем нужные колонки
    outliers = (returns["monthly_past_return"] > 1) | (returns["monthly_past_return"] < -0.5)  # маска выбросов
    outliers = returns[outliers].reset_index().sort_values("date")  # сортируем по дате
    return outliers.head(limit)  # первые limit выбросов


def _save_outliers(outliers: pd.DataFrame, output_path: Path) -> None:
    """Сохранить список выбросов в текстовый файл."""
    # Сохраняем найденные выбросы в текстовый файл.
    output_path.parent.mkdir(parents=True, exist_ok=True)  # создаем папку
    lines = []  # буфер строк
    for _, row in outliers.iterrows():  # перебор выбросов
        lines.append(f"{row['ticker']}, {row['date'].date()}, {row['price']}")  # формат строки
    output_path.write_text("\n".join(lines), encoding="utf-8")  # запись файла


def plot_average_price(prices_long: pd.DataFrame, results_dir: Path, plot: bool = False):
    """Построить и сохранить график средней цены по всем акциям."""
    # Считаем среднюю цену по каждому месяцу.
    avg_price = prices_long.groupby(level="date")["price"].mean()  # средняя цена по дате
    plot_path = results_dir / "plots" / "avg_price.png"  # путь к графику
    plot_path.parent.mkdir(parents=True, exist_ok=True)  # создаем папку

    # Строим и сохраняем график.
    fig = plt.figure(figsize=(10, 5))  # создаем фигуру
    plt.plot(avg_price.index, avg_price.values)  # линия средней цены
    plt.title("Average Stock Price Over Time")  # заголовок
    plt.xlabel("Date")  # подпись оси X
    plt.ylabel("Average Price")  # подпись оси Y
    plt.tight_layout()  # компактные отступы
    plt.savefig(plot_path)  # сохраняем в файл

    if plot:  # если хотим вернуть фигуру
        return fig  # возвращаем объект фигуры

    plt.close(fig)  # закрываем фигуру, чтобы не держать память
    return None  # если не требуется вернуть фигуру


def preprocess_prices(prices: pd.DataFrame, results_dir: Path) -> pd.DataFrame:
    """Выполнить полную предобработку цен акций и сохранить артефакты."""
    # Переводим цены в long-формат и приводим к месячной частоте.
    prices_long = _reshape_prices(prices)  # long-формат
    prices_long = _filter_price_range(prices_long)  # фильтр цен
    prices_long = _compute_returns(prices_long)  # расчет доходностей

    # Сохраняем небольшую выборку выбросов и строим диагностический график.
    outliers = _detect_outliers(prices_long)  # поиск выбросов
    _save_outliers(outliers, results_dir / "outliers.txt")  # запись выбросов
    plot_average_price(prices_long, results_dir, plot=False)  # график средней цены

    # Заменяем выбросы и заполняем пропуски.
    prices_long = _replace_outlier_returns(prices_long)  # замена выбросов на NaN
    prices_long = _fill_missing(prices_long)  # заполнение и удаление NaN

    # Выводим контроль остаточных пропусков.
    print(prices_long.isna().sum())  # контроль остаточных NaN
    return prices_long  # возвращаем очищенные цены



def preprocess_sp500(sp500: pd.DataFrame) -> pd.DataFrame:
    """Привести индекс S&P 500 к месячной частоте и рассчитать доходность."""
    # Приводим индекс к месячной частоте и считаем доходность.
    sp500 = sp500.copy()  # копия
    sp500 = sp500.set_index("Date").sort_index()  # Date в индекс
    sp500 = _monthly_last(sp500)  # месячная частота
    sp500["monthly_return"] = sp500["Adjusted Close"].pct_change()  # доходность индекса
    sp500 = sp500.dropna()  # удаляем первые NaN
    return sp500  # возвращаем индекс


def preprocessing(prices: pd.DataFrame, sp500: pd.DataFrame, results_dir: str | Path = "results") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Точка входа: подготовить цены акций и индекс S&P 500."""
    # Общая точка входа: возвращает очищенные цены и индекс.
    results_path = Path(results_dir)  # путь к результатам
    prices_clean = preprocess_prices(prices, results_path)  # чистим цены
    sp500_clean = preprocess_sp500(sp500)  # чистим индекс
    return prices_clean, sp500_clean  # возвращаем обе таблицы
