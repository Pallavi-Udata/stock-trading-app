import yfinance as yf
import pandas as pd
import numpy as np
import ta

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ==============================
# YOUR PORTFOLIO
# ==============================
portfolio = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS"
]

# ==============================
# FUNCTION TO ANALYZE STOCK
# ==============================
def analyze_stock(stock):
    try:
        df = yf.download(stock, period="2y", interval="1d")

        if df.empty:
            return None

        close = df['Close'].squeeze()

        # Indicators
        df['RSI'] = ta.momentum.RSIIndicator(close).rsi()
        df['MA20'] = close.rolling(window=20).mean()
        df['MA50'] = close.rolling(window=50).mean()
        df['EMA20'] = close.ewm(span=20).mean()
 
        macd = ta.trend.MACD(close)
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()

        df['Volume_Change'] = df['Volume'].pct_change()
        df['Price_Change'] = close.pct_change()

        # Trend
        df['Trend'] = (df['MA20'] > df['MA50']).astype(int)

        # Target
        df['Target'] = ((close.shift(-1) / close) > 1.002).astype(int)

        # Clean
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        if len(df) < 100:
            return None

        # Features
        X = df[['RSI', 'MA20', 'MA50', 'EMA20',
                'MACD', 'MACD_signal',
                'Volume_Change', 'Price_Change',
                'Trend']]

        y = df['Target']

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )

        # Scaling
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)

        # Model
        model = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.03,
            eval_metric='logloss'
        )

        model.fit(X_train, y_train)

        # Predict latest
        latest = X.iloc[-1:]
        latest_scaled = scaler.transform(latest)

        prob = model.predict_proba(latest_scaled)[0][1]

        return prob

    except Exception as e:
        print(f"Error in {stock}: {e}")
        return None


# ==============================
# ANALYZE PORTFOLIO
# ==============================
print("\n💼 PORTFOLIO ANALYSIS:\n")

for stock in portfolio:
    prob = analyze_stock(stock)

    if prob is None:
        continue

    confidence = round(prob * 100, 2)

    if confidence > 70:
        decision = "BUY MORE 📈"
    elif confidence > 50:
        decision = "HOLD 🤝"
    else:
        decision = "SELL 📉"

    print(f"{stock} → {decision} ({confidence}%)")