
import requests
import pandas as pd
from datetime import datetime
from ta.trend import MACD, EMAIndicator
from ta.momentum import RSIIndicator

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = "8168191121:AAEYiwekg24YCq8izhlXQ6bXh pVjL-TJ7HK"  # Remplace avec ton token de bot Telegram
TELEGRAM_CHAT_ID = "525275970"      # Remplace avec ton ID de chat Telegram
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 500  # Nombre de bougies à récupérer

# === FONCTIONS ===

def fetch_binance_ohlcv(symbol, interval, limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def add_indicators(df):
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    df["ema_20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    macd = MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    return df

def detect_double_bottom(df):
    lows = df['low'].tail(20)
    min_low = lows.min()
    count = (lows <= min_low * 1.02).sum()
    if count >= 2:
        return "Double Bottom"
    return None

def detect_breakout(df):
    last_close = df['close'].iloc[-1]
    recent_high = df['high'].rolling(20).max().iloc[-2]
    recent_low = df['low'].rolling(20).min().iloc[-2]
    if last_close > recent_high:
        return "Breakout Haussier"
    elif last_close < recent_low:
        return "Breakout Baissier"
    return None

def detect_head_and_shoulders(df):
    closes = df['close'].tail(20).values
    if len(closes) < 7:
        return None
    left = closes[-7]
    head = closes[-4]
    right = closes[-1]
    if left < head > right and abs(left - right) < 0.02 * head:
        return "Tête et épaules"
    return None

def confirm_signal(df):
    latest = df.iloc[-1]
    confirmation = []
    if latest["rsi"] < 30:
        confirmation.append("RSI < 30")
    if latest["macd"] > latest["macd_signal"]:
        confirmation.append("MACD haussier")
    if latest["close"] > latest["ema_20"]:
        confirmation.append("Cours > EMA20")
    return confirmation

def determine_action(confirmation):
    if "RSI < 30" in confirmation and "MACD haussier" in confirmation:
        return "BUY"
    elif "MACD haussier" not in confirmation and "Cours > EMA20" not in confirmation:
        return "SELL"
    else:
        return "ATTENTE"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

# === LOGIQUE PRINCIPALE ===
df = fetch_binance_ohlcv(SYMBOL, INTERVAL, LIMIT)
df = add_indicators(df)

patterns_detected = []

for detector in [detect_double_bottom, detect_breakout, detect_head_and_shoulders]:
    result = detector(df)
    if result:
        patterns_detected.append(result)

if patterns_detected:
    confirmations = confirm_signal(df)
    action = determine_action(confirmations)
    timestamp = df.index[-1].strftime("%Y-%m-%d %H:%M")
    alert_msg = f"ALERTE BTCUSD - {timestamp}
"                 f"Patterns détectés : {', '.join(patterns_detected)}
"                 f"Confirmations : {', '.join(confirmations) if confirmations else 'Aucune'}
"                 f"Recommandation : {action}"
    send_telegram_alert(alert_msg)

alert_msg if patterns_detected else "Aucune alerte détectée pour le moment."
