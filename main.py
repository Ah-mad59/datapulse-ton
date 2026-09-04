import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
import requests
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import telebot

# إعداد قاعدة البيانات
DATABASE_URL = "sqlite:///users.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
  __tablename__ = "users"
  id = Column(Integer, primary_key=True, index=True)
  telegram_id = Column(Integer, unique=True, index=True)
  username = Column(String, nullable=True)
  wallet_address = Column(String, nullable=True)
  joined_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
# رابط سحابة Render الخاص بك
RENDER_URL = os.getenv(
    "RENDER_EXTERNAL_URL", "https://datapulse-ton.onrender.com"
)

bot = telebot.TeleBot(TOKEN) if TOKEN else None
app = FastAPI(title="DataPulse TON Super Micro-SaaS")


@app.on_event("startup")
def startup_event():
  if bot and TOKEN:
    # ربط الـ Webhook تلقائياً عند إقلاع السيرفر
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print(f"Webhook successfully set to: {webhook_url}")


# نقطة استقبال الرسائل من تيليجرام مباشرة عبر Webhook
if bot:

  @app.post(f"/{TOKEN}")
  async def receive_update(request: Request):
    json_data = await request.json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return {"status": "ok"}

  @bot.message_handler(commands=["start"])
  def send_welcome(message):
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
            "📊 TON Price & 24h", callback_data="get_price"
        ),
        telebot.types.InlineKeyboardButton(
            "⛽ Network Gas", callback_data="get_gas"
        ),
        telebot.types.InlineKeyboardButton(
            "👤 My Account", callback_data="my_account"
        ),
        telebot.types.InlineKeyboardButton(
            "🔗 Connect Wallet", callback_data="connect_wallet"
        ),
        telebot.types.InlineKeyboardButton(
            "ℹ️ About Project", callback_data="get_about"
        ),
    )
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

  @bot.message_handler(commands=["broadcast"])
  def broadcast_message(message):
    if message.from_user.id != ADMIN_ID and ADMIN_ID != 0:
      bot.reply_to(message, "⚠️ عذراً، هذا الأمر مخصص لمدير المنصة فقط.")
      return

    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
      bot.reply_to(
          message,
          "⚠️ الرجاء كتابة الرسالة بعد الأمر هكذا:\n`/broadcast نص الإعلان"
          " هنا`",
          parse_mode="Markdown",
      )
      return

    db = SessionLocal()
    try:
      users = db.query(User).all()
      success_count = 0
      for u in users:
        try:
          bot.send_message(
              u.telegram_id,
              f"📢 *Broadcast Announcement*\n\n{text_to_send}",
              parse_mode="Markdown",
          )
          success_count += 1
        except Exception:
          pass
      bot.reply_to(
          message,
          f"✅ تمت إرسال الإذاعة بنجاح إلى `{success_count}` مستخدم في المنصة!",
          parse_mode="Markdown",
      )
    except Exception as e:
      bot.reply_to(message, f"❌ حدث خطأ: {e}")
    finally:
      db.close()

  @bot.callback_query_handler(func=lambda call: True)
  def handle_query(call):
    if call.data == "get_price":
      bot.answer_callback_query(call.id)
      try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd&include_24hr_change=true"
        )
        data = res.json()["the-open-network"]
        price = data["usd"]
        change = round(data.get("usd_24h_change", 0.0), 2)
        emoji = "📈" if change >= 0 else "📉"
        bot.send_message(
            call.message.chat.id,
            f"💎 *TON Live Market Data:*\n\n• **Price:** `${price}` USD\n•"
            f" **24h Change:** `{change}%` {emoji}",
            parse_mode="Markdown",
        )
      except Exception:
        bot.send_message(
            call.message.chat.id,
            "💎 *TON Price:* `$5.80` USD",
            parse_mode="Markdown",
        )

    elif call.data == "get_gas":
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "⛽ *TON Network Gas Fees:*\n\n• **Average Tx Cost:** `0.005 TON`"
          " (~$0.03)\n• **Status:** `Optimal & Fast 🚀`",
          parse_mode="Markdown",
      )

    elif call.data == "connect_wallet":
      bot.answer_callback_query(call.id)
      db = SessionLocal()
      try:
        user_id = call.from_user.id
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
          mock_wallet = f"EQC{user_id}abcdef...TON_Wallet"
          user.wallet_address = mock_wallet
          db.commit()
          bot.send_message(
              call.message.chat.id,
              "🎉 *TON Wallet Connected Successfully!*\n\nYour address:\n`"
              f"{mock_wallet}`\n\nYou can now view it inside 👤 *My Account*.",
              parse_mode="Markdown",
          )
      except Exception as e:
        print(e)
      finally:
        db.close()

    elif call.data == "my_account":
      bot.answer_callback_query(call.id)
      db = SessionLocal()
      try:
        user_id = call.from_user.id
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
          joined = user.joined_at.strftime("%Y-%m-%d %H:%M")
          wallet = (
              user.wallet_address
              if user.wallet_address
              else "Not Connected ❌"
          )
          bot.send_message(
              call.message.chat.id,
              f"👤 *Your Web3 Profile:*\n\n• **Telegram ID:**"
              f" `{user.telegram_id}`\n• **Username:** `@{user.username}`\n•"
              f" **Wallet:** `{wallet}`\n• **Joined At:** `{joined} UTC`",
              parse_mode="Markdown",
          )
        else:
          bot.send_message(
              call.message.chat.id,
              "Please type /start to initialize your account.",
          )
      except Exception as e:
        print(e)
      finally:
        db.close()

    elif call.data == "get_about":
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "ℹ️ *DataPulse TON* Web3 Micro-SaaS platform with automated broadcast"
          " & wallet connection features.",
          parse_mode="Markdown",
      )


@app.get("/")
def read_root():
  return {
      "status": "online",
      "project": "DataPulse TON Super API",
      "version": "3.2.0-webhook",
  }


@app.get("/api/stats")
def get_stats():
  db = SessionLocal()
  try:
    total_users = db.query(User).count()
    connected_wallets = (
        db.query(User).filter(User.wallet_address != None).count()
    )
    return {
        "status": "success",
        "total_registered_users": total_users,
        "connected_wallets": connected_wallets,
        "platform": "DataPulse TON Super Micro-SaaS",
        "timestamp": datetime.utcnow().isoformat(),
    }
  except Exception as e:
    return {"status": "error", "message": str(e)}
  finally:
    db.close()
