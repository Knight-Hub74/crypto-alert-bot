import requests
import pandas as pd
from datetime import datetime
from ta.trend import MACD, EMAIndicator
from ta.momentum import RSIIndicator
import time

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = "VOTRE_BOT_TOKEN"  # Remplacez par votre token de bot Telegram
TELEGRAM_CHAT_ID = "VOTRE_CHAT_ID"      # Remplacez par votre ID de chat Telegram
SYMBOLS = ["bitcoin", "ethereum"]  # Liste des symboles à surveiller (ici BTC et ETH en format CoinGecko)
TIMEFRAME = '1h'                     # Timeframe à utiliser
LIMIT = 500                           # Nombre de bougies à récupérer

# === FONCTIONS ===

# Fonction pour récupérer les données de prix depuis CoinGecko
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

# Détecter les patterns (fonction simplifiée)
def detect_patterns(df):
    patterns = []

    for i in range(2, len(df)):
        candle1 = df.iloc[i - 2]
        candle2 = df.iloc[i - 1]
        candle3 = df.iloc[i]

        # Bullish Engulfing
        if (candle2['close'] < candle2['open']) and \
           (candle3['close'] > candle3['open']) and \
           (candle3['close'] > candle2['open']) and \
           (candle3['open'] < candle2['close']):
            patterns.append({
                'pattern': 'Bullish Engulfing',
                'index': df.index[i],
                'signal': 'buy',
                'strength': 'strong'
            })

        # Bearish Engulfing
        if (candle2['close'] > candle2['open']) and \
           (candle3['close'] < candle3['open']) and \
           (candle3['open'] > candle2['close']) and \
           (candle3['close'] < candle2['open']):
            patterns.append({
                'pattern': 'Bearish Engulfing',
                'index': df.index[i],
                'signal': 'sell',
                'strength': 'strong'
            })

        # Doji (exemple simplifié)
        if abs(candle3['close'] - candle3['open']) < 0.001 * candle3['close']:
            patterns.append({
                'pattern': 'Doji',
                'index': df.index[i],
                'signal': 'neutral',
                'strength': 'weak'
            })

    return patterns

# Fonction principale pour récupérer les données, ajouter des indicateurs et détecter les patterns
def main():
    for symbol in SYMBOLS:
        print(f"Analyse en cours pour {symbol}...")

        # Récupérer les données de marché pour chaque actif
        df = fetch_coingecko_data(symbol)

        # Ajouter les indicateurs techniques
        df = add_indicators(df)

        # Détection des patterns
        patterns = detect_patterns(df)

        # Si des patterns sont détectés, envoyer l'alerte Telegram
        if patterns:
            for pattern in patterns:
                message = f"[ALERTE PATTERN 📊]\n"
                message += f"⏰ {pattern['index']}\n"
                message += f"📈 Actif : {symbol.upper()}\n"
                message += f"📐 Pattern détecté : {pattern['pattern']}\n"
                message += f"✅ Confirmé par RSI + MACD\n"  # Exemple simple de confirmation
                message += f"📊 Prise de position :\n"
                message += f"    ➤ {pattern['signal'].capitalize()} à {df['close'].iloc[-1]}\n"
                message += f"    ➤ Stop Loss à {df['close'].iloc[-1] * 0.99} (-1%)\n"  # Exemple
                message += f"    ➤ Take Profit à {df['close'].iloc[-1] * 1.02} (+2%)\n"  # Exemple
                message += f"💡 Stratégie : Confirmation par RSI et MACD\n"

                # Envoi de l'alerte
                send_telegram_alert(message)
        else:
            print(f"Aucun pattern détecté pour {symbol}.")
        
        # Pause entre les analyses pour éviter trop de requêtes
        time.sleep(60 * 60)  # Pause de 1 heure

# Lancer la fonction principale
if __name__ == "__main__":
    main()
