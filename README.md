# Backtesting S&P 500

Проект для бэктестинга стратегии Stock Picking 20 на исторических данных S&P 500.
Данные приводятся к месячной частоте (берется последнее значение месяца), выбросы фильтруются, а пропуски заполняются внутри каждого тикера.

## Структура
```
.
├── data/
│   ├── sp500.csv
│   └── stock_prices.csv
├── notebook/
│   └── analysis.ipynb
├── results/
│   ├── outliers.txt
│   ├── results.txt
│   └── plots/
│       ├── avg_price.png
│       ├── avg_price_by_company.png
│       └── strategy_vs_sp500.png
├── scripts/
│   ├── backtester.py
│   ├── create_signal.py
│   ├── memory_reducer.py
│   ├── preprocessing.py
│   └── main.py
└── requirements.txt
```

## Установка (с чистого окружения)
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск
```
python3 scripts/main.py
```
Результаты сохраняются в `results/`:
- `results.txt` — итоговый PnL и доходность стратегии и S&P 500
- `outliers.txt` — первые 5 выбросов (ticker, date, price)
- `plots/` — графики (все с заголовками)

## Анализ в ноутбуке
`notebook/analysis.ipynb` выполняет:
- анализ пропусков (по переменным и по годам),
- анализ выбросов,
- график средней цены по времени и по каждой компании,
- внешнюю сверку 5 выбросов (через `yfinance`, требуется интернет).

## Описание файлов
- `scripts/memory_reducer.py` — читает CSV, приводит дату к `datetime`, уменьшает память (без уменьшения ниже `float32`).
- `scripts/preprocessing.py` — агрегация по месяцам (последнее значение), фильтр цен [0.1; 10000], расчет past/future returns, обработка выбросов, заполнение пропусков внутри тикера, сохранение `outliers.txt` и графиков.
- `scripts/create_signal.py` — считает `average_return_1y` (12 месяцев) и формирует `signal` для топ‑20 компаний в каждом месяце.
- `scripts/backtester.py` — считает PnL как `signal * future_return`, считает доходность как `PnL / sum(signal)`, строит накопленный PnL.
- `scripts/main.py` — полный pipeline от загрузки до бэктеста и сохранения результатов.

## Заключение
По состоянию на 30 января 2026:
- Стратегия Stock Picking 20: Total PnL = 67.73, Total Return = 0.0217
- S&P 500: Total PnL = 11.59, Total Return = 0.0032

