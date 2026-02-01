"""Загрузка CSV с оптимизацией памяти для цен акций и индекса S&P 500."""

from __future__ import annotations  # future-совместимость аннотаций типов

from pathlib import Path  # пути к файлам
from typing import Dict, Tuple  # типы для подсказок

import numpy as np  # численные типы
import pandas as pd  # таблицы и CSV




def _reduce_mem_usage(df: pd.DataFrame) -> pd.DataFrame:
    """Снизить потребление памяти DataFrame за счет даункаста типов."""
    # Уменьшаем память: float -> float32, int -> меньший int, object -> category.
    for col in df.columns:  # перебор колонок
        if pd.api.types.is_datetime64_any_dtype(df[col]):  # дату не трогаем
            continue  # переход к следующей колонке

        if pd.api.types.is_numeric_dtype(df[col]):  # если числовая колонка
            if pd.api.types.is_float_dtype(df[col]):  # float -> float32
                df[col] = df[col].astype(np.float32)  # уменьшение памяти
            else:
                df[col] = pd.to_numeric(df[col], downcast="integer")  # int -> меньший int
            continue  # числовую колонку обработали

        if df[col].dtype == object:  # текстовые колонки
            num_unique = df[col].nunique(dropna=True)  # число уникальных
            num_total = len(df[col])  # длина колонки
            if num_total > 0 and num_unique / num_total < 0.5:  # мало уникальных
                df[col] = df[col].astype("category")  # переводим в category

    return df  # возвращаем оптимизированный df


def _read_csv(path: Path) -> pd.DataFrame:
    """Прочитать CSV, распарсить даты и оптимизировать память."""
    # Читаем CSV и приводим Date к datetime.
    df = pd.read_csv(path)  # чтение CSV
    if "Date" in df.columns:  # если есть колонка Date
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")  # парсинг дат
    return _reduce_mem_usage(df)  # оптимизация памяти


def memory_reducer(paths: Dict[str, str | Path]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Загрузить цены и индекс S&P 500 с оптимизацией памяти."""
    # Загружаем цены акций и S&P 500 с оптимизацией памяти.
    prices_path = Path(paths["prices"]).expanduser()  # путь к ценам акций
    sp500_path = Path(paths["sp500"]).expanduser()  # путь к индексу

    prices = _read_csv(prices_path)  # загрузка и оптимизация цен
    sp500 = _read_csv(sp500_path)  # загрузка и оптимизация индекса

    return prices, sp500  # возвращаем два датафрейма
