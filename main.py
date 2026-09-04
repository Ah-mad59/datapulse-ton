import os
import threading
from fastapi import FastAPI, Depends, HTTPException
import telebot
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="DataPulse TON API")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN) if TOKEN else None

if bot:

  @bot.message_handler(commands=["start"])
  def send_welcome(message):
    welcome_text = (
        "⚡️ *Welcome to DataPulse TON* \n\n"
        "Your advanced gateway to TON network data and Web3 analytics. 🚀\n\n"
        "Choose what you'd like to explore below."
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")


# استخدام حدث بدء التشغيل لضمان عمل البوت ورؤية حالته في الـ Logs
@app.on_event("startup")
def startup_event():
  if bot:

    def run_bot():
      try:
        print("Telegram bot polling started successfully...")
        bot.infinity_polling(none_stop=True)
      except Exception as e:
        print(f"Bot polling error: {e}")

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
  else:
    print(
        "WARNING: TELEGRAM_BOT_TOKEN is missing or invalid! Bot will not run."
    )


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


@app.get("/")
def read_root():
  return {
      "message": "Welcome to DataPulse TON Backend API is running successfully!"
  }
