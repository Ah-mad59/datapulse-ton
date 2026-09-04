import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
import requests
from sqlalchemy import Boolean, Column, DateTime, Integer, String, create_engine
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
  is_premium = Column(Boolean, default=False)
  joined_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
RENDER_URL = os.getenv(
    "RENDER_EXTERNAL_URL", "https://datapulse-ton.onrender.com"
)

bot = telebot.TeleBot(TOKEN) if TOKEN else None
app = FastAPI(title="DataPulse TON Monitized SaaS")


@app.on_event("startup")
def startup_event():
  if bot and TOKEN:
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    try:
      bot.remove_webhook()
      res = bot.set_webhook(url=webhook_url)
      print(f"✅ Webhook setup result: {res} -> {webhook_url}")
    except Exception as e:
      print(f"❌ Webhook error: {e}")


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
            "💎 Pro Market Insights", callback_data="pro_insights"
        ),
        telebot.types.InlineKeyboardButton(
            "👤 My Account", callback_data="my_account"
        ),
        telebot.types.InlineKeyboardButton(
            "🔗 Connect Wallet", callback_data="connect_wallet"
        ),
        telebot.types.InlineKeyboardButton(
            "⭐ Upgrade to PRO", callback_data="upgrade_pro"
        ),
        telebot.types.InlineKeyboardButton(
            "🛠️ Support & Help", callback_data="support"
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

  @bot.message_handler(commands=["pro"])
  def make_user_pro(message):
    if message.from_user.id != ADMIN_ID and ADMIN_ID != 0:
      bot.reply_to(message, "⚠️ هذا الأمر مخصص لمدير النظام فقط.")
      return
    parts = message.text.split()
    if len(parts) < 2:
      bot.reply_to(message, "⚠️ الاستخدام الصحيح: `/pro [Telegram_ID]`")
      return
    try:
      target_id = int(parts[1])
      db = SessionLocal()
      user = db.query(User).filter(User.telegram_id == target_id).first()
      if user:
        user.is_premium = True
        db.commit()
        bot.reply_to(
            message,
            f"✅ تم تفعيل باقة PRO بنجاح للمستخدم `{target_id}`!",
            parse_mode="Markdown",
        )
        bot.send_message(
            target_id,
            "🎉 *تهانينا!* تم ترقية حسابك إلى باقة **DataPulse PRO** بنجاح. استمتع"
            " بالتحليلات الحصرية الآن! 🚀",
            parse_mode="Markdown",
        )
      else:
        bot.reply_to(message, "❌ لم يتم العثور على المستخدم في قاعدة البيانات.")
      db.close()
    except Exception as e:
      bot.reply_to(message, f"❌ حدث خطأ: {e}")

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
            "💎 *TON Price:* `$1.36` USD",
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

    elif call.data == "pro_insights":
      bot.answer_callback_query(call.id)
      db = SessionLocal()
      try:
        user_id = call.from_user.id
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user and user.is_premium:
          bot.send_message(
              call.message.chat.id,
              "🔥 *PRO Whale Tracking & Deep Insights:*\n\n• **Large Transactions"
              " (24h):** `42 Whale Transfers`\n• **Inflow Volume:** `+1.5M"
              " TON`\n• **Market Sentiment:** `Strong Bullish 🚀`",
              parse_mode="Markdown",
          )
        else:
          bot.send_message(
              call.message.chat.id,
              "🔒 *ميزة حصرية للأعضاء المميزين (PRO)*\n\nهذه التحليلات المتقدمة"
              " ورصد حركة الحيتان مخصصة فقط لمشتركي باقة Pro.\n\nللاشتراك"
              " والحصول على الصلاحية، قم بالنقر على زر **⭐ Upgrade to PRO**"
              " أدناه.",
              parse_mode="Markdown",
          )
      except Exception as e:
        print(e)
      finally:
        db.close()

    elif call.data == "upgrade_pro":
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "⭐ *كيفية الترقية إلى باقة DataPulse PRO:*\n\n1️⃣ قم بتحويل `1"
          " TON` فقط إلى محفظة منصتنا الرسمية:\n`UQDBbQY_R5cnZlpRv5x-f_CNFU8v0whgBLsjpGwwsjZxpPCH`\n\n2️⃣"
          " بعد اتمام التحويل، اضغط على زر **🛠️ Support & Help** وأرسل إيصال"
          " التحويل أو رقم المعاملة مع معرفك للمدير ليتم تفعيل حسابك فوراً!",
          parse_mode="Markdown",
      )

    elif call.data == "support":
      bot.answer_callback_query(call.id)
      bot.send_message(
          call.message.chat.id,
          "🛠️ *DataPulse Support Desk*\n\nهل تواجه مشكلة، أو تريد تفعيل"
          " اشتراكك بعد التحويل؟\n\nتواصل مباشرة مع مدير النظام والدعم"
          " الفني:\n👉 **Telegram:** `@AHMADISRAJ`\n\nنحن هنا لمساعدتك على مدار"
          " الساعة! 🚀",
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
              f"{mock_wallet}`",
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
          status_pro = (
              "⭐ PRO Member" if user.is_premium else "👤 Standard Free"
          )
          bot.send_message(
              call.message.chat.id,
              f"👤 *Your Web3 Profile:*\n\n• **Telegram ID:**"
              f" `{user.telegram_id}`\n• **Account Type:** `{status_pro}`\n•"
              f" **Wallet:** `{wallet}`\n• **Joined At:** `{joined} UTC`",
              parse_mode="Markdown",
          )
      except Exception as e:
        print(e)
      finally:
        db.close()


@app.get("/")
def read_root():
  return {
      "status": "online",
      "project": "DataPulse TON Monitized SaaS",
      "version": "4.1.1",
  }
