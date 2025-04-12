import requests
import pandas as pd
from ta.trend import MACD, EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime
import numpy as np
import ccxt
import time

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = "7695512134:AAHOwinoUzeqUFREW7GnClkmf20Hod3_TYs"  # Remplacez par votre token de bot Telegram
TELEGRAM_CHAT_ID = "5252757970"      # Remplacez par votre ID de chat Telegram
SYMBOLS = ["BTC/USDT", "EUR/USD"]       # Liste des symboles à surveiller
TIMEFRAME = '1h'                        # Timeframe à utiliser
LIMIT = 500                              # Nombre de bougies à récupérer

# === FONCTIONS ===

# Fonction pour récupérer les données OHLCV depuis Binance
def fetch_coingecko_data(symbol, currency="usd"):
    url = f'https://api.coingecko.com/api/v3/coins/{symbol}/market_chart'
    params = {'vs_currency': currency, 'days': '1', 'interval': 'hourly'}
    response = requests.get(url, params=params)
    data = response.json()
    
    prices = data['prices']
    df = pd.DataFrame(prices, columns=['timestamp', 'close'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# Ajouter des indicateurs techniques (RSI, MACD, EMA)
def add_indicators(df):
    df["rsi"] = RSIIndicator(df["close"]).rsi()
    df["ema_20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    macd = MACD(close=df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    return df

# Fonction pour envoyer les alertes sur Telegram
def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            print("Message envoyé avec succès sur Telegram!")
        else:
            print(f"Erreur lors de l'envoi du message. Code : {response.status_code}")
            print("Détails de l'erreur:", response.json())
    except Exception as e:
        print(f"Une erreur s'est produite lors de l'envoi du message : {str(e)}")

# Fonction de détection des patterns chartistes classiques
def detect_patterns(df):
    patterns = []

    for i in range(2, len(df)):
        candle1 = df.iloc[i - 2]
        candle2 = df.iloc[i - 1]
        candle3 = df.iloc[i]

        # ENGULFING BULLISH
        if (candle2['close'] < candle2['open']) and \
           (candle3['close'] > candle3['open']) and \
           (candle3['close'] > candle2['open']) and \
           (candle3['open'] < candle2['close']):
            patterns.append({
                'pattern': 'Bullish Engulfing',
                'index': df.index[i],
                'signal': 'buy',
                'strength': 'strong',
                'confirmation': 'RSI + MACD',
                'entry': candle3['close'],
                'stop_loss': candle3['low'],
                'take_profit': candle3['high'] * 1.05,  # Exemple : TP à +5% du high
                'strategy': 'Confirmer la cassure du précédent plus bas'
            })

        # ENGULFING BEARISH
        if (candle2['close'] > candle2['open']) and \
           (candle3['close'] < candle3['open']) and \
           (candle3['open'] > candle2['close']) and \
           (candle3['close'] < candle2['open']):
            patterns.append({
                'pattern': 'Bearish Engulfing',
                'index': df.index[i],
                'signal': 'sell',
                'strength': 'strong',
                'confirmation': 'RSI + MACD',
                'entry': candle3['close'],
                'stop_loss': candle3['high'],
                'take_profit': candle3['low'] * 0.95,  # Exemple : TP à -5% du low
                'strategy': 'Confirmer la cassure du précédent plus haut'
            })

        # ... (autres patterns à ajouter selon le besoin)

    return patterns

# Fonction principale pour récupérer les données, ajouter des indicateurs et détecter les patterns
def main():
    for symbol in SYMBOLS:
        print(f"Analyse en cours pour {symbol}...")
        df = fetch_binance_ohlcv(symbol)
        df = add_indicators(df)

        # Détection des patterns
        patterns = detect_patterns(df)

        if patterns:
            for pattern in patterns:
                # Formater le message avec les détails
                message = f"[ALERTE PATTERN 📊]\n"
                message += f"⏰ {pattern['index']}\n"
                message += f"📈 Actif : {symbol}\n"
                message += f"📐 Pattern détecté : {pattern['pattern']}\n"
                message += f"✅ Confirmé par {pattern['confirmation']}\n"
                message += f"📊 Prise de position :\n"
                message += f"    ➤ {pattern['signal'].capitalize()} à {pattern['entry']}\n"
                message += f"    ➤ Stop Loss à {pattern['stop_loss']}\n"
                message += f"    ➤ Take Profit à {pattern['take_profit']}\n"
                message += f"💡 Stratégie : {pattern['strategy']}\n"
                
                send_telegram_alert(message)
        else:
            print(f"Aucun signal de trading détecté pour {symbol}.")
        
        # Pause entre les analyses pour éviter trop de requêtes
        time.sleep(60 * 60)  # Pause de 1 heure

# Lancer la fonction principale
if __name__ == "__main__":
    main()
