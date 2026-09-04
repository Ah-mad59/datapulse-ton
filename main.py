import requests
from telebot import types

# إعدادات محفظة استلام الأرباح وتون سنتر
TONCENTER_API = "https://toncenter.com/api/v2/getTransactions"
MY_WALLET = "EQD...ضع_عنوان_محفظتك_هنا..."  # ضع عنوان محفظتك هنا

# دالة فحص المعاملات من شبكة TON
def verify_ton_transaction(user_id: int) -> bool:
    params = {
        "address": MY_WALLET,
        "limit": 10,
        "archival": True
    }
    try:
        response = requests.get(TONCENTER_API, params=params)
        data = response.json()
        
        if data.get("ok"):
            transactions = data.get("result", [])
            for tx in transactions:
                in_msg = tx.get("in_msg", {})
                message_text = in_msg.get("message", "") # الـ Memo أو التعليق المرسل مع التحويل
                value = int(in_msg.get("value", 0))     # القيمة بالـ Nanoton
                
                # التحقق من أن التعليق يحتوي على الـ user_id وأن المبلغ 0.5 TON على الأقل (500,000,000 نانون)
                if str(user_id) in message_text and value >= 500_000_000:
                    return True
        return False
    except Exception as e:
        print(f"Error checking transaction: {e}")
        return False

# مستمع ضغطة زر "تحقق من الدفع" في البوت
@bot.callback_query_handler(func=lambda call: call.data == "check_payment")
def handle_check_payment(call):
    user_id = call.from_user.id
    
    # استدعاء دالة الفحص
    is_paid = verify_ton_transaction(user_id)
    
    if is_paid:
        # فتح جلسة قاعدة البيانات وتحديث حالة المستخدم إلى مشترك (is_premium = True)
        db = SessionLocal() # تأكد أن SessionLocal معرف لديك في المشروع
        user = db.query(User).filter(User.telegram_id == user_id).first() # استبدل User بجدول المستخدمين لديك
        
        if user:
            user.is_premium = True  # تأكد أن هذا الحقل موجود في جدول المستخدمين
            db.commit()
        db.close()
        
        # إعلام المستخدم بنجاح العملية
        bot.answer_callback_query(call.id, "✅ تم التحقق وتفعيل اشتراكك بنجاح!")
        bot.edit_message_text(
            "🎉 **مبروك! تم تفعيل اشتراكك في DataPulse TON بنجاح.**\n"
            "يمكنك الآن الاستمتاع بكافة الميزات المتقدمة.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        # إذا لم يتم العثور على التحويل بعد
        bot.answer_callback_query(
            call.id, 
            "❌ لم يتم العثور على التحويل بعد. تأكد من إتمام الدفع مع كتابة رقمك التعريفي في التعليق.", 
            show_alert=True
        )

