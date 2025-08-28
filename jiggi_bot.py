import telebot
import yfinance as yf
import pandas_ta as ta
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

LOG_FILE = "bot_log.txt"  # log fayl nomi

# -----------------------------
# Log yozish funksiyasi
# -----------------------------
def log_write(text):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{timestamp} - {text}\n")
    except:
        pass

# -----------------------------
# Terminalda log chiqarish
# -----------------------------
def safe_print(text):
    try:
        print(text)
        log_write(text)
    except:
        pass

# -----------------------------
# Signal olish funksiyasi
# -----------------------------
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

# -----------------------------
# Signalni chatga yuborish
# -----------------------------
def send_signal_chat(sym, tf):
    key = f"{sym}_{tf}"
    sig, price, rsi = get_signal(sym, tf)

    if sig == "ERROR":
        msg = f"⚠️ {sym} ({tf}) ma'lumot topilmadi yoki xato yuz berdi."
        safe_print(msg)
        try:
            bot.send_message(ADMIN_CHAT_ID, msg)
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
        log_write(f"{sym} ({tf}) signal yuborildi: {sig}")

# -----------------------------
# Parallel signal yuborish
# -----------------------------
def send_signals():
    threads = []
    for sym in symbols:
        for tf in timeframes:
            t = Thread(target=send_signal_chat, args=(sym, tf))
            t.start()
            threads.append(t)
    for t in threads:
        t.join()

# -----------------------------
# Heartbeat: bot ishga tushganini xabar qiladi
# -----------------------------
def heartbeat():
    msg = f"💓 Bot ishga tushgan / ish holati: {datetime.now().strftime('%H:%M:%S')}"
    safe_print(msg)
    try:
        bot.send_message(ADMIN_CHAT_ID, msg)
    except:
        pass

# -----------------------------
# Asosiy loop
# -----------------------------
safe_print("🚀 Signal Bot ishga tushdi...")

heartbeat_interval = 10 * 60  # 10 daqiqa
last_heartbeat = time.time()

while True:
    try:
        send_signals()
        
        # Heartbeat tekshiruvi
        if time.time() - last_heartbeat >= heartbeat_interval:
            heartbeat()
            last_heartbeat = time.time()
        
        time.sleep(30)  # har 30 sekund signal tekshirish
    except Exception as e:
        safe_print(f"❌ Botda xato: {e}")
        try:
            bot.send_message(ADMIN_CHAT_ID, f"❌ Botda xato: {e}")
        except:
            pass
        time.sleep(5)
