import os
import time
import logging
import schedule
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import telebot
from datetime import datetime
from threading import Thread

# ================== LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_log.txt"),
        logging.StreamHandler()
    ]
)

# ================== BOT TOKEN ==================
# ❗ xavfsizlik uchun tokenni env orqali olishni maslahat beraman
# Linux/Mac: export BOT_TOKEN="TOKEN"
# Windows: set BOT_TOKEN=TOKEN
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_CHAT_ID = 1864871417  # Admin uchun xatolik yuboriladi
CHAT_IDS = [1864871417, 7870026222]

bot = telebot.TeleBot(TOKEN)

# ================== SYMBOLS & SETTINGS ==================
symbols = ["BTC-USD", "GC=F", "EURUSD=X"]  # GC=F = Gold Futures
timeframes = ["1m", "5m"]
last_signal = {}

# ================== SIGNAL FUNCTION ==================
def get_signal(symbol, interval):
    try:
        df = yf.download(symbol, period="5d", interval=interval, auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError(f"{symbol} ({interval}) uchun ma'lumot topilmadi.")

        df["EMA50"] = ta.ema(df["Close"], length=50)
        df["EMA200"] = ta.ema(df["Close"], length=200)
        df["RSI"] = ta.rsi(df["Close"], length=14)

        last = df.iloc[-1]
        if pd.isna(last["EMA50"]) or pd.isna(last["EMA200"]) or pd.isna(last["RSI"]):
            raise ValueError(f"{symbol} ({interval}) uchun EMA/RSI qiymatlari NaN.")

        signal = "NO"
        if last["EMA50"] > last["EMA200"] and last["RSI"] < 30:
            signal = "BUY"
        elif last["EMA50"] < last["EMA200"] and last["RSI"] > 70:
            signal = "SELL"

        return signal, last["Close"], last["RSI"]

    except Exception as e:
        logging.error(f"Signal olishda xato: {symbol} ({interval}) - {str(e)}")
        return "ERROR", None, None

# ================== SEND SIGNAL FUNCTION ==================
def send_signal_chat(sym, tf):
    key = f"{sym}_{tf}"
    sig, price, rsi = get_signal(sym, tf)

    if sig == "ERROR":
        try:
            bot.send_message(ADMIN_CHAT_ID, f"⚠️ {sym} ({tf}) ma'lumot topilmadi yoki xato yuz berdi.")
        except Exception as e:
            logging.error(f"Admin chatga xabar yuborishda xato: {str(e)}")
        return

    if sig in ["BUY", "SELL"] and last_signal.get(key) != sig:
        message = (
            f"📊 {sym} Signal: {sig} ({tf})\n"
            f"💰 Price: {price:.2f}\n"
            f"📈 RSI: {rsi:.2f}\n"
            f"🕒 Time: {datetime.now().strftime('%H:%M:%S')}"
        )
        for chat_id in CHAT_IDS:
            try:
                bot.send_message(chat_id, message)
                logging.info(f"Signal yuborildi: {sym} ({tf}) - {sig} to {chat_id}")
            except Exception as e:
                logging.error(f"{chat_id} ga yuborishda xato: {str(e)}")
        last_signal[key] = sig
    elif sig == "NO":
        logging.info(f"{sym} ({tf}) uchun signal yo'q (NO).")

# ================== MULTI-THREAD SIGNAL CHECK ==================
def send_signals():
    threads = []
    for sym in symbols:
        for tf in timeframes:
            t = Thread(target=send_signal_chat, args=(sym, tf))
            t.start()
            threads.append(t)

    for t in threads:
        t.join()

# ================== SCHEDULE LOOP ==================
def run_bot():
    schedule.every(1).minutes.do(send_signals)
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Bot loopda xato: {str(e)}")
            time.sleep(60)

# ================== MAIN ==================
if __name__ == "__main__":
    logging.info("Bot ishga tushdi.")
    try:
        bot_thread = Thread(target=run_bot)
        bot_thread.start()
        bot.polling(non_stop=True)
    except Exception as e:
        logging.error(f"Bot pollingda xato: {str(e)}")
