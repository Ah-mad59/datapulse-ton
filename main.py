import os
import threading
from fastapi import FastAPI
import telebot
import requests
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# إعداد قاعدة البيانات
DATABASE_URL = "sqlite:///users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
  __tablename__ = "users"
  id = Column(Integer, primary_key=True, index=True)
  telegram_id = Column(Integer, unique=True, index=True)
  username = Column(String, nullable=True)
  joined_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN) if TOKEN else None
app = FastAPI(title="DataPulse TON API")


@app.on_event("startup")
def startup_event():
  if bot:

    def run_bot():
      try:
        bot.remove_webhook()
        bot.infinity_polling(none_stop=True, skip_pending=True)
      except Exception as e:
        print(f"Bot polling error: {e}")

    threading.Thread(target=run_bot, daemon=True).start()


if bot:

  @bot.message_handler(commands=["start"])
  def send_welcome(message):
    # حفظ المستخدم في قاعدة البيانات
    db = SessionLocal()
    try:
      user_id = message.from_user.id
      username = message.from_user.username or "No Username"
      existing_user = db.query(User).filter(User.telegram_id == user_id).first()
      if not existing_user:
        new_user = User(telegram_id=user_id, username=username)
        db.add(new_user)
        db.commit()
    except Exception as e:
      print(f"DB Error: {e}")
    finally:
      db.close()

    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton(
            "📊 TON Price", callback_data="get_price"
        ),
        telebot.types.InlineKeyboardButton(
            "⛽ Network Gas", callback_data="get_gas"
        ),
        telebot.types.InlineKeyboardButton(
            "ℹ️ About Project", callback_data="get_about"
        ),
    )
    bot.send_message(
        message.chat.id,
        "⚡️ *Welcome to DataPulse TON* \n\nYour advanced gateway to TON network"
        " data and Web3 analytics. 🚀\n\n👇 *Choose an option below to"
        " explore:*",
        parse_mode="Markdown",
        reply_markup=markup,
    )

  @bot.callback_query_handler(func=lambda call: True)
  def handle_query(call):
    if call.data == "get_price":
      bot.answer_callback_query(call.id)
      try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd"
        )
        price = res.json()["the-open-network"]["usd"]
        bot.send_message(
            call.message.chat.id,
            f"💎 *Current TON Price:* `${price}` USD",
            parse_mode="Markdown",
        )
      except Exception:
        bot.send_message(
            call.message.chat.id,
            "💎 *TON Price:* $5.80 (Estimated)",
            parse_mode="Markdown",
        )
    elif call.data == "get_gas":
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "⛽ *TON Network Gas Fees:* `0.005 TON`",
          parse_mode="Markdown",
      )
    elif call.data == "get_about":
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "ℹ️ *DataPulse TON* Micro-SaaS analytics platform.",
          parse_mode="Markdown",
      )


@app.get("/")
def read_root():
  return {"message": "DataPulse TON API with Database is running!"}
