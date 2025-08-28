import telebot
import yfinance as yf
import pandas_ta as ta
import schedule
import time
from datetime import datetime
from threading import Thread

# Telegram token va admin chat
TOKEN = "8407649391:AAFCXRPDTl1Oh64jxh-PBDUjc-Vkg_BqaO4"
ADMIN_CHAT_ID = 1864871417  # xatoliklarni yuborish uchun

CHAT_IDS = [1864871417, 7870026222]

bot = telebot.TeleBot(TOKEN)

symbols = ["BTC-USD", "GC=F", "EURUSD=X"]  # GC=F = Gold Futures
timeframes = ["1m", "5m"]
last_signal = {}

# Signal olish funksiyasi
def get_signal(symbol, interval):
    try:
        df = yf.download(symbol, period="5d", interval=interval, auto_adjust=True, progress=False)
        if df.empty:
            return "ERROR", None, None
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

# Signal yuborish funksiyasi (chatga)
def send_signal_chat(sym, tf):
    key = f"{sym}_{tf}"
    sig, price, rsi = get_signal(sym, tf)

    if sig == "ERROR":
        safe_print(f"{sym} ({tf}) ma'lumot topilmadi yoki xato yuz berdi.")
        # Telegramga admin chatga xatolik yuborish
        try:
            bot.send_message(ADMIN_CHAT_ID, f"⚠️ {sym} ({tf}) ma'lumot topilmadi yoki xato yuz berdi.")
        except:
            pass
        return

    if last_signal.get(key) != sig and sig in ["BUY", "SELL"]:
        message = (
            f"{sym} Signal: {sig} ({tf})\n"
            f"Price: {price:.2f}\n"
            f"RSI: {rsi:.2f}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        for chat_id in CHAT_IDS:
            try:
                bot.send_message(chat_id, message)
            except Exception as e:
                safe_print(f"{chat_id} ga yuborishda xato: {e}")
        last_signal[key] = sig

# Terminalda loglarni xavfsiz chiqarish
def safe_print(text):
    try:
        print(text)
    except:
        pass

# Parallel signal yuborish
def send_signals():
    threads = []
    for sym in symbols:
        for tf in timeframes:
            t = Thread(target=send_signal_chat, args=(sym, tf))
            t.start()
