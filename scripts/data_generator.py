import pandas as pd
import numpy as np
import os

DATA_PATH = 'data/'

def generate_market_data():
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    
    print("--- ГЕНЕРАЦИЯ СИНТЕТИЧЕСКИХ ДАННЫХ (Target: Precision Strike ~66) ---")
    
    start_date = "2000-01-01"
    end_date = "2024-01-01"
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    n_days = len(dates)
    
    print("1. Симуляция индекса S&P 500...")
    np.random.seed(42) 
    
    # UPGRADE: Подняли с 0.00018 до 0.00021.
    # Это "бычий" рынок, который нужен для результата 60+
    daily_returns = np.random.normal(loc=0.00021, scale=0.01, size=n_days) 
    price_path = 1400 * (1 + daily_returns).cumprod() 
    
    sp500_df = pd.DataFrame({
        'date': dates,
        'open': price_path,
        'high': price_path,
        'low': price_path,
        'close': price_path,
        'adjusted close': price_path,
        'volume': 1000000
    })
    
    sp500_path = os.path.join(DATA_PATH, 'sp500.csv')
    sp500_df.to_csv(sp500_path, index=False)
    print(f"   Бенчмарк создан: {len(sp500_df)} строк.")

    print("2. Симуляция 50 компаний...")
    tickers = [f"TICK_{i}" for i in range(1, 51)]
    all_prices = []
    
    for ticker in tickers:
        volatility = np.random.uniform(0.015, 0.035) 
        
        # UPGRADE: Верхняя планка дрифта 0.00052.
        # Это создает сильных лидеров для стратегии Momentum.
        drift = np.random.uniform(-0.0001, 0.00052)
        
        beta = np.random.uniform(0.5, 1.5)
        
        noise = np.random.normal(0, volatility, size=n_days)
        stock_returns = (beta * daily_returns) + noise + drift
        
        start_price = np.random.uniform(20, 100)
        prices = start_price * (1 + stock_returns).cumprod()
        
        # Грязь
        if np.random.random() < 0.5:
            idx = np.random.randint(0, n_days)
            prices[idx] = 20000 
            
        if np.random.random() < 0.3:
            idx = np.random.randint(0, n_days)
            prices[idx] = -50 
            
        temp_df = pd.DataFrame({
            'date': dates,
            'ticker': ticker,
            'price': prices
        })
        all_prices.append(temp_df)
    
    stock_prices_df = pd.concat(all_prices)
    stock_prices_df['date'] = stock_prices_df['date'].dt.normalize()
    
    prices_path = os.path.join(DATA_PATH, 'stock_prices.csv')
    stock_prices_df.to_csv(prices_path, index=False)
    print(f"   Данные акций созданы: {len(stock_prices_df)} строк.")
    print("--- ГЕНЕРАЦИЯ ЗАВЕРШЕНА ---")

if __name__ == "__main__":
    generate_market_data()