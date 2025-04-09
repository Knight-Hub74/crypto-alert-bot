import requests
import logging
import pandas as pd
from datetime import datetime
from ta.trend import MACD, EMAIndicator
from ta.momentum import RSIIndicator

# === CONFIGURATION ===
logging.basicConfig(level=logging.DEBUG)
TELEGRAM_BOT_TOKEN = "8168191121:AAEYiwekg24YCq8izhlXQ6bXh pVjL-TJ7HK"  # Remplace avec ton token de bot Telegram
TELEGRAM_CHAT_ID = "525275970"      # Remplace avec ton ID de chat Telegram
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 500  # Nombre de bougies à récupérer

# === FONCTIONS ===

def fetch_binance_ohlcv(symbol, interval, limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    
    # Vérification du code de statut HTTP
    if response.status_code != 200:
        logging.error(f"Erreur lors de la requête API : {response.status_code}")
        return pd.DataFrame()  # Retourner un DataFrame vide si erreur
    
    data = response.json()
    
    # Vérification que les données ne sont pas vides
    if not data:
        logging.error("Aucune donnée reçue de l'API.")
        return pd.DataFrame()  # Retourner un DataFrame vide si aucune donnée
    
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # Vérification que le DataFrame contient des données
    if df.empty:
        logging.error("Le DataFrame est vide après récupération des données.")
        return df
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    
    logging.debug(f"Extrait du DataFrame : \n{df.head()}")
    
    return df

def add_indicators(df):
    if df.empty:
        logging.error("Le DataFrame est vide, impossible d'ajouter des indicateurs.")
        return df
    
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    df["ema_20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    macd = MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    return df

def detect_double_bottom(df):
    if df.empty:
        logging.error("Le DataFrame est vide, impossible de détecter des patterns.")
        return None
    
    lows = df['low'].tail(20)
    min_low = lows.min()
    count = (lows <= min_low * 1.02).sum()
    if count >= 2:
        return "Double Bottom"
    return None

def detect_breakout(df):
    if df.empty:
        logging.error("Le DataFrame est vide, impossible de détecter des breakout.")
        return None
    
    last_close = df['close'].iloc[-1] if len(df) > 0 else None
    recent_high = df['high'].rolling(20).max().iloc[-2] if len(df) > 1 else None
    recent_low = df['low'].rolling(20).min().iloc[-2] if len(df) > 1 else None
    
    if last_close is not None and recent_high is not None and recent_low is not None:
        if last_close > recent_high:
            return "Breakout Haussier"
        elif last_close < recent_low:
            return "Breakout Baissier"
    return None

def detect_head_and_shoulders(df):
    if df.empty:
        logging.error("Le DataFrame est vide, impossible de détecter des patterns.")
        return None
    
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
    if df.empty:
        logging.error("Le DataFrame est vide, impossible de confirmer le signal.")
        return []
    
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
if not df.empty:
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
        alert_msg = f"ALERTE BTCUSD - {timestamp}\n" \
                f"Patterns détectés : {', '.join(patterns_detected)}\n" \
                f"Confirmations : {', '.join(confirmations) if confirmations else 'Aucune'}\n" \
                f"Recommandation : {action}"
        send_telegram_alert(alert_msg)
else:
    logging.error("Aucune donnée valide reçue, le programme s'arrête.")
