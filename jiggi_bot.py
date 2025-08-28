import telebot
import yfinance as yf
import pandas_ta as ta
import schedule
import time
from datetime import datetime
from threading import Thread
import logging

# Logging sozlamalari: xatolarni faylga yozish va konsolga chiqarish
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_log.txt"),
        logging.StreamHandler()
    ]
)

# Telegram token va admin chat
TOKEN = "8407649391:AAFCXRPDTl1Oh64jxh-PBDUjc-Vkg_BqaO4"
ADMIN_CHAT_ID = 1864871417  # xatoliklarni yuborish uchun

CHAT_IDS = [1864871417, 7870026222]

bot = telebot.TeleBot(TOKEN)

symbols = ["BTC-USD", "GC=F", "EURUSD=X"]  # GC=F = Gold Futures
timeframes = ["1m", "5m"]
last_signal = {}

# Signal olish funksiyasi (yaxshilangan xatolarni boshqarish)
def get_signal(symbol, interval):
    try:
        df = yf.download(symbol, period="5d", interval=interval, auto_adjust=True, progress=False)
        if df.empty:
            raise ValueError(f"{symbol} ({interval}) uchun ma'lumot topilmadi.")
        
        df["EMA50"] = ta.ema(df["Close"], length=50)
        df["EMA200"] = ta.ema(df["Close"], length=200)
        df["RSI"] = ta.rsi(df["Close"], length=14)
        
        # NaN qiymatlarni tekshirish (emas bo'lsa, signal bermaymiz)
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

# Signal yuborish funksiyasi (chatga, faqat yangi signal bo'lsa)
def send_signal_chat(sym, tf):
    key = f"{sym}_{tf}"
    sig, price, rsi = get_signal(sym, tf)

    if sig == "ERROR":
        # Admin chatga xatolik yuborish
        try:
            bot.send_message(ADMIN_CHAT_ID, f"⚠️ {sym} ({tf}) ma'lumot topilmadi yoki xato yuz berdi.")
        except Exception as e:
            logging.error(f"Admin chatga xabar yuborishda xato: {str(e)}")
        return

    # Faqat BUY yoki SELL bo'lsa va oldingi signal farq qilsa yuboramiz
    if sig in ["BUY", "SELL"] and last_signal.get(key) != sig:
        message = (
            f"{sym} Signal: {sig} ({tf})\n"
            f"Price: {price:.2f}\n"
            f"RSI: {rsi:.2f}\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
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

# Parallel signal yuborish (optimallashtirilgan)
def send_signals():
    threads = []
    for sym in symbols:
        for tf in timeframes:
            t = Thread(target=send_signal_chat, args=(sym, tf))
            t.start()
            threads.append(t)
    # Barcha threadlarni kutish (optimallashtirish uchun)
    for t in threads:
        t.join()

# Botni doimiy ishlash uchun jadval (har 1 daqiqada tekshirish)
def run_bot():
    schedule.every(1).minutes.do(send_signals)
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logging.error(f"Bot loopda xato: {str(e)}")
            time.sleep(60)  # Xato bo'lsa, 1 daqiqa kutib qayta urinish

# Asosiy ishga tushirish
if __name__ == "__main__":
    logging.info("Bot ishga tushdi.")
    try:
        bot.polling(non_stop=True)  # Botni doimiy eshitish uchun (agar kerak bo'lsa)
    except Exception as e:
        logging.error(f"Bot pollingda xato: {str(e)}")
    
    # Parallel ravishda signal jadvalini ishga tushirish
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
