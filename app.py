import streamlit as st
from auto_trading_system import analyze_stock, get_market_trend, calculate_target, calculate_stop_loss
import yfinance as yf
import pandas as pd
import time
import matplotlib.pyplot as plt
import ta

def get_signal_explanation(signal, confidence, trend):
    if signal == "BUY 📈":
        return {
            "reason": "Strong momentum + market trend is positive",
            "action": "Good time to enter or add position"
        }

    elif signal == "HOLD":
        if trend != "UP":
            return {
                "reason": "Market trend is weak or sideways",
                "action": "Wait before entering, hold if already invested"
            }
        else:
            return {
                "reason": "Moderate strength but not strong breakout",
                "action": "Wait for confirmation before buying"
            }

    else:  # AVOID
        return {
            "reason": "Weak stock, low probability of profit",
            "action": "Do not enter, look for better opportunities"
        }

# ======================
# SESSION STATE
# ======================
if "analyze_clicked" not in st.session_state:
    st.session_state.analyze_clicked = False

# ======================
# STOCK MAP
# ======================
stock_map = {
    "reliance": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infy": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "icici": "ICICIBANK.NS",
    "sbi": "SBIN.NS",
    "vbl": "VBL.NS"
}

def get_stock_symbol(user_input):
    user_input = user_input.lower().strip()
    if ".ns" in user_input:
        return user_input.upper()
    return stock_map.get(user_input, None)

# ======================
# LIVE PRICE FUNCTION
# ======================
def get_live_price(stock):
    ticker = yf.Ticker(stock)

    # Try 1-minute data first
    data = ticker.history(period="1d", interval="1m")

    if data is not None and not data.empty:
        return float(data['Close'].iloc[-1])

    # 🔁 FALLBACK to 5-minute data
    data = ticker.history(period="1d", interval="5m")

    if data is not None and not data.empty:
        return float(data['Close'].iloc[-1])

    # 🔁 FINAL fallback (daily)
    data = ticker.history(period="1d")

    if data is not None and not data.empty:
        return float(data['Close'].iloc[-1])

    return None
# ======================
# UI
# ======================
st.title("📊 AI Stock Trading App")

user_input = st.text_input("🔍 Enter Stock (e.g. infy, vbl)", "vbl")

if st.button("Analyze Stock"):
    st.session_state.analyze_clicked = True

# ======================
# TABLE (BEFORE CLICK)
# ======================
if not st.session_state.analyze_clicked:

    st.subheader("📊 Top AI Stock Picks")

    stocks = ["RELIANCE.NS", "TCS.NS", "INFY.NS",
              "HDFCBANK.NS", "ICICIBANK.NS", "LT.NS", "SBIN.NS"]

    data = []
    trend = get_market_trend()

    for s in stocks:
        result = analyze_stock(s)

        if result:
            prob, price = result
            confidence = round(prob * 100, 2)

            if confidence > 70 and trend == "UP":
                signal = "BUY 📈"
            elif confidence > 50:
                signal = "HOLD"
            else:
                signal = "AVOID ❌"

            data.append({
                "Stock": s,
                "Signal": signal,
                "Confidence (%)": confidence
            })

    st.dataframe(pd.DataFrame(data))

# ======================
# ANALYSIS AFTER CLICK
# ======================
if st.session_state.analyze_clicked:

    stock = get_stock_symbol(user_input)

    if not stock:
        st.error("❌ Stock not found")
    else:
        st.subheader(f"📊 {stock}")

        placeholder = st.empty()

        for _ in range(50):  # live loop

            with placeholder.container():

                # ======================
                # LIVE PRICE
                # ======================
                ticker = yf.Ticker(stock)
                live_df = ticker.history(period="1d", interval="1m")

                if live_df.empty:
                    st.error("No live data")
                    break

                live_price = float(live_df['Close'].iloc[-1])

                # ======================
                # AI ANALYSIS
                # ======================
                result = analyze_stock(stock)

                if result:
                    prob, _ = result
                    confidence = round(prob * 100, 2)

                    trend = get_market_trend()
                    # ======================
                    # CALCULATE INDICATORS FOR SCORE
                    # ======================
                    df = ticker.history(period="5d", interval="5m")

                    close = df['Close'].squeeze()

                    # RSI
                    rsi = ta.momentum.RSIIndicator(close).rsi().iloc[-1]

                    # MA50
                    ma50 = close.rolling(50).mean().iloc[-1]

                    # ======================
                    # SCORING SYSTEM
                    # ======================
                    score = 0

                    # AI Confidence (max 50)
                    score += confidence * 0.5

                    # Market Trend
                    if trend == "UP":
                        score += 20
                    elif trend == "DOWN":
                        score -= 10

                    # RSI
                    if rsi < 30:
                        score += 15
                    elif rsi > 70:
                        score -= 10

                    # Moving Average
                    if live_price > ma50:
                        score += 15

                    # Normalize score (optional)
                    score = max(0, min(100, round(score, 2)))
                    
                    
                    if confidence > 70 and trend == "UP":
                        signal = "BUY 📈"
                    elif confidence > 50:
                        signal = "HOLD"
                    else:
                        signal = "AVOID ❌"

                    sl = calculate_stop_loss(live_price)
                    target = calculate_target(live_price)

                    # ======================
                    # DISPLAY METRICS
                    # ======================
                    st.metric("💰 Live Price", round(live_price, 2))
                    st.write(f"⭐ Score: {score}/100")

                    explanation = get_signal_explanation(signal, confidence, trend)

                    st.write(f"🧠 Reason: {explanation['reason']}")
                    st.write(f"👉 Action: {explanation['action']}")
                    st.write(f"🎯 Confidence: {confidence}%")
                    st.write(f"🎯 Target: {target}")
                    st.write(f"🛑 Stop Loss: {sl}")

                # ======================
                # CHART DATA
                # ======================
                df = ticker.history(period="5d", interval="5m")

                if df.empty:
                    st.error("No chart data")
                    break

                close = df['Close'].squeeze()

                # Indicators
                df['MA20'] = close.rolling(20).mean()
                df['MA50'] = close.rolling(50).mean()

                df['RSI'] = ta.momentum.RSIIndicator(close).rsi()

                macd = ta.trend.MACD(close)
                df['MACD'] = macd.macd()
                df['MACD_signal'] = macd.macd_signal()

                # ======================
                # PLOT
                # ======================
                fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

                ax1.plot(df.index, close, label="Price")
                ax1.plot(df.index, df['MA20'], label="MA20")
                ax1.plot(df.index, df['MA50'], label="MA50")

                ax1.axhline(live_price, linestyle='--', label='Live Price')

                ax1.legend()
                ax1.set_title(f"{stock} Chart")

                ax2.plot(df.index, df['RSI'])
                ax2.axhline(70, linestyle='--')
                ax2.axhline(30, linestyle='--')
                ax2.set_title("RSI")

                ax3.plot(df.index, df['MACD'], label="MACD")
                ax3.plot(df.index, df['MACD_signal'], label="Signal")
                ax3.legend()
                ax3.set_title("MACD")

                st.pyplot(fig)

            time.sleep(2)

# ======================
# RESET
# ======================
if st.button("🔄 Reset"):
    st.session_state.analyze_clicked = False