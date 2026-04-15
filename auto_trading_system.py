import yfinance as yf
import pandas as pd
import numpy as np
import ta
import datetime
import sys
import requests

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# ==============================
# TELEGRAM FUNCTION
# ==============================
def send_telegram_message(message):
    bot_token = "8713505656:AAFQv87TP440zFL5lpL2MWVlE4zdvTb9nO8"   # ⚠️ Replace
    chat_id = "7844339886"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message})


# ==============================
# FILE LOGGING
# ==============================
today = datetime.date.today()
filename = f"AI_Report_{today}.txt"

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        pass

sys.stdout = Logger(filename)

# ==============================
# SETTINGS
# ==============================
stocks = ["RELIANCE.NS", "TCS.NS", "INFY.NS",
          "HDFCBANK.NS", "ICICIBANK.NS", "LT.NS", "SBIN.NS"]

portfolio = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]

# ==============================
# FUNCTIONS
# ==============================
def calculate_stop_loss(price):
    return round(price * 0.98, 2)

def calculate_target(price):
    return round(price * 1.03, 2)

def get_market_trend():
    try:
        df = yf.download("^NSEI", period="6mo", interval="1d")

        # ✅ Handle empty data
        if df is None or df.empty:
            return "UNKNOWN"

        close = df['Close'].squeeze()

        # Moving average
        ma50 = close.rolling(50).mean()

        # Compare last values
        if close.iloc[-1] > ma50.iloc[-1]:
            return "UP"
        else:
            return "DOWN"

    except Exception as e:
        print("Market trend error:", e)
        return "UNKNOWN"
    close = df['Close'].squeeze()
    ma50 = close.rolling(50).mean()

    return "UP" if close.iloc[-1] > ma50.iloc[-1] else "DOWN"

def analyze_stock(stock):
    try:
        df = yf.download(stock, period="2y", interval="1d")
        if df.empty:
            return None

        close = df['Close'].squeeze()

        df['RSI'] = ta.momentum.RSIIndicator(close).rsi()
        df['MA20'] = close.rolling(20).mean()
        df['MA50'] = close.rolling(50).mean()
        df['EMA20'] = close.ewm(span=20).mean()

        macd = ta.trend.MACD(close)
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()

        df['Volume_Change'] = df['Volume'].pct_change()
        df['Price_Change'] = close.pct_change()
        df['Trend'] = (df['MA20'] > df['MA50']).astype(int)

        df['Target'] = ((close.shift(-1) / close) > 1.002).astype(int)

        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        if len(df) < 100:
            return None

        X = df[['RSI','MA20','MA50','EMA20',
                'MACD','MACD_signal',
                'Volume_Change','Price_Change','Trend']]

        y = df['Target']

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False)

        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)

        model = XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.03,
            eval_metric='logloss'
        )

        model.fit(X_train, y_train)

        latest = X.iloc[-1:]
        latest_scaled = scaler.transform(latest)

        prob = model.predict_proba(latest_scaled)[0][1]
        price = close.iloc[-1]

        return prob, price

    except Exception as e:
        print(f"Error in {stock}: {e}")
        return None


# ==============================
# RUN SYSTEM
# ==============================
print(f"\nDATE: {today}")
print("="*50)

market_trend = get_market_trend()
print(f"Market Trend: {market_trend}")

# ==============================
# TOP PICKS
# ==============================
results = []

for stock in stocks:
    print(f"Processing {stock}...")
    result = analyze_stock(stock)

    if result:
        prob, price = result
        results.append((stock, prob, price))

results = sorted(results, key=lambda x: x[1], reverse=True)

print("\n" + "="*50)
print("TOP AI STOCK PICKS")
print("="*50)

for stock, prob, price in results[:5]:
    confidence = round(prob * 100, 2)
    sl = calculate_stop_loss(price)
    target = calculate_target(price)

    if confidence > 70:
        if market_trend == "DOWN":
            signal = "WAIT ⚠️ (Market Weak)"
        else:
            signal = "BUY 📈"
    elif confidence > 50:
        signal = "HOLD"
    else:
        signal = "AVOID ❌"

    print(f"{stock} → {signal}")
    print(f"   Entry: {round(price,2)} | Target: {target} | SL: {sl}")

# ==============================
# PORTFOLIO
# ==============================
print("\n" + "="*50)
print("PORTFOLIO ANALYSIS")
print("="*50)

portfolio_results = []

for stock in portfolio:
    result = analyze_stock(stock)
    if result:
        prob, price = result
        confidence = round(prob * 100, 2)

        if confidence > 70:
            decision = "HOLD ⚠️" if market_trend == "DOWN" else "BUY MORE 📈"
        elif confidence > 50:
            decision = "HOLD"
        else:
            decision = "SELL"

        portfolio_results.append((stock, decision, confidence))

        print(f"{stock} → {decision} ({confidence}%)")

print("\n✅ Report saved successfully!")

# ==============================
# TELEGRAM MESSAGE
# ==============================
message = "🔥 AI TRADING SIGNAL\n\n"
message += f"Market Trend: {market_trend}\n\n"

message += "TOP PICKS:\n\n"

for stock, prob, price in results[:5]:
    confidence = round(prob * 100, 2)
    sl = calculate_stop_loss(price)
    target = calculate_target(price)

    if confidence > 70:
        if market_trend == "DOWN":
            signal = "WAIT ⚠️"
        else:
            signal = "BUY"
    elif confidence > 50:
        signal = "HOLD"
    else:
        signal = "AVOID"

    message += f"{stock} → {signal}\n"
    message += f"Entry: {round(price,2)}\nTarget: {target}\nSL: {sl}\n\n"
    
message += "\nPORTFOLIO:\n"
for stock, decision, confidence in portfolio_results:
    message += f"{stock} → {decision} ({confidence}%)\n"

send_telegram_message(message)