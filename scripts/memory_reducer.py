import pandas as pd
import numpy as np

def reduce_memory_usage(df):
    """
    Уменьшает потребление памяти DataFrame.
    ВАЖНО: Пропускает колонки 'date' и 'ticker', чтобы не испортить их.
    """
    start_mem = df.memory_usage().sum() / 1024**2
    print(f'Memory usage of dataframe is {start_mem:.2f} MB')

    # Список колонок, которые НЕЛЬЗЯ трогать
    # Приводим к нижнему регистру для сравнения
    skip_cols = ['date', 'ticker', 'symbol', 'date', 'Date', 'Ticker']

    for col in df.columns:
        # Если колонка в списке исключений - пропускаем
        if col.lower() in [x.lower() for x in skip_cols]:
            continue

        col_type = df[col].dtype

        # Если это не число (объект), пробуем превратить в число, 
        # НО только если это не похоже на дату
        if col_type == object:
            try:
                # Пробуем преобразовать, но если получится много NaN, откатываем назад
                converted = pd.to_numeric(df[col], errors='coerce')
                # Если более 50% данных стали NaN, значит это был текст (не число)
                if converted.isna().sum() / len(converted) > 0.5:
                    pass # Оставляем как есть (текст)
                else:
                    df[col] = converted
                    col_type = df[col].dtype
            except:
                pass

        # Оптимизация чисел
        if col_type != object and not pd.api.types.is_datetime64_any_dtype(df[col]):
            c_min = df[col].min()
            c_max = df[col].max()

            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                    df[col] = df[col].astype(np.int64)
            else:
                # Используем float32 (требование ТЗ)
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)

    end_mem = df.memory_usage().sum() / 1024**2
    print(f'Memory usage after optimization is: {end_mem:.2f} MB')
    print(f'Decreased by {100 * (start_mem - end_mem) / start_mem:.1f}%')

    return df