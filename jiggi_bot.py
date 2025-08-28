import telebot
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import schedule
import time
from datetime import datetime

# Token
TOKEN = "8407649391:AAFCXRPDTl1Oh64jxh-PBDUjc-Vkg_BqaO4"

# Bir nechta odam/guruh chat_id larini yoz
CHAT_IDS = [ 1864871417, 7870026222]  # bu yerga o'zingning va boshqalarning chat_id larini qo'sh

bot = telebot.TeleBot(TOKEN)

symbols = ["BTC-USD", "XAUUSD=X", "EURUSD=X"]
timeframes = ["1m", "5m"]
last_signal = {}

def get_signal(symbol, interval):
    try:
        df = yf.download(symbol, period="5d", interval=interval)
        df["EMA50"] = ta.ema(df["Close"], length=50)
        df["EMA200"] = ta.ema(df["Close"], length=200)
        df["RSI"] = ta.rsi(df["Close"], length=14)
        last = df.iloc[-1]
        signal = "NO"
        if last["EMA50"] > last["EMA200"] and last["RSI"] < 30:
            signal = "BUY"
        elif last["EMA50"] < last["EMA200"] and last["RSI"] > 70:
            signal = "SELL"
        return signal, last["Close"], last["RSI"]
    except Exception as e:
        return "ERROR", None, None

def send_signals():
    global last_signal
    for sym in symbols:
        for tf in timeframes:
            key = f"{sym}_{tf}"
            sig, price, rsi = get_signal(sym, tf)
            if last_signal.get(key) != sig and sig in ["BUY", "SELL"]:
                message = (
                    f"{sym} Signal: {sig} ({tf})\n"
                    f"Price: {price:.2f}\n"
                    f"RSI: {rsi:.2f}\n"
                    f"Time: {datetime.now().strftime('%H:%M:%S')}"
                )
                for chat_id in CHAT_IDS:   # <<< Hamma odamga yuboradi
                    try:
                        bot.send_message(chat_id, message)
                    except Exception as e:
                        print(f"{chat_id} ga yuborishda xato: {e}")
                last_signal[key] = sig
            time.sleep(1)

# Terminalda loglarni qisqartirish uchun
def safe_print(text):
    try:
        print(text)
    except:
        pass

schedule.every(1).minutes.do(send_signals)

safe_print("Signal Bot ishga tushdi...")

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        safe_print(f"Xato: {e}")
        time.sleep(5)
