import os
import threading
from fastapi import FastAPI
import telebot
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN) if TOKEN else None

app = FastAPI(title="DataPulse TON API")


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


if bot:

  @bot.message_handler(commands=["start"])
  def send_welcome(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    btn_price = telebot.types.InlineKeyboardButton(
        "📊 TON Price", callback_data="get_price"
    )
    btn_gas = telebot.types.InlineKeyboardButton(
        "⛽ Network Gas", callback_data="get_gas"
    )
    btn_about = telebot.types.InlineKeyboardButton(
        "ℹ️ About Project", callback_data="get_about"
    )
    markup.add(btn_price, btn_gas, btn_about)

    welcome_text = (
        "⚡️ *Welcome to DataPulse TON* \n\n"
        "Your advanced gateway to TON network data and Web3 analytics. 🚀\n\n"
        "👇 *Choose an option below to explore:*"
    )
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=markup,
    )

  @bot.callback_query_handler(func=lambda call: True)
  def handle_query(call):
    if call.data == "get_price":
      bot.answer_callback_query(call.id)
      # جلب سعر TON الحقيقي من API عام
      try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd"
        )
        price = res.json()["the-open-network"]["usd"]
        bot.send_message(
            call.message.chat.id,
            f"💎 *Current TON Price:* `${price}` USD\n📈 Market is active and tracking live.",
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
          "⛽ *TON Network Gas Fees:*\nAverage transaction cost: `0.005 TON`"
          " (Very Low & Fast 🚀)",
          parse_mode="Markdown",
      )

    elif call.data == "get_about":
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "ℹ️ *DataPulse TON* is a smart Micro-SaaS built on FastAPI & Render"
          " to provide instant Web3 data analytics.",
          parse_mode="Markdown",
      )


@app.get("/")
def read_root():
  return {
      "message": "Welcome to DataPulse TON Backend API is running successfully!"
  }
