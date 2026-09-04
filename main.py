import os
import threading
import telebot
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine

# إنشاء الجداول في قاعدة البيانات تلقائياً
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DataPulse TON API")

# إعداد بوت تليجرام
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN) if TOKEN else None

if bot:
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        welcome_text = (
            "👋 **Welcome to DataPulse TON | أهلاً بك!**\n\n"
            "Your advanced gateway to TON network data and Web3 analytics. 🚀\n"
            "بوابتك المتطورة لبيانات وتحليلات شبكة TON وعالم الـ Web3.\n\n"
            "Choose what you'd like to explore below / اختر ما تود استكشافه لبدء رحلتك."
        )
        bot.reply_to(message, welcome_text, parse_mode="Markdown")

    # تشغيل البوت في الخلفية ليتوافق مع سيرفر الويب على Render
    def run_bot():
        bot.infinity_polling()

    threading.Thread(target=run_bot, daemon=True).start()

# الاتصال بقاعدة البيانات لكل طلب
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to DataPulse TON Backend API is running successfully!"}
