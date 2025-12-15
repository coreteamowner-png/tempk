import os
import random
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("TEMPMAIL_API_KEY")
BASE_URL = "https://chat-tempmail.com"

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

URDU_SHAYARI = [
    "تمہارا غم ہی تو ہے جو ہمیں زندہ رکھتا ہے — جون ایلیا",
    "سنا ہے لوگ اُسے آنکھوں میں بساتے ہیں — احمد فراز",
    "ہم بھی دریا ہیں ہمیں اپنا ہنر معلوم ہے — جون ایلیا",
    "رنجش ہی سہی دل ہی دکھانے کے لیے آ — احمد فراز",
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "👑 *MuDaSiR VIP Temp Mail Bot* 👑\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{random.choice(URDU_SHAYARI)}\n\n"
        f"خوش آمدید {user.mention_markdown_v2()}"
    )

    keyboard = [[InlineKeyboardButton("📧 نیا ای میل بنائیں", callback_data="create")]]

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    # 🔹 GET DOMAINS
    if q.data == "domains":
        r = requests.get(f"{BASE_URL}/api/email/domains", headers=HEADERS)
        domains = r.json().get("domains", [])
        msg = "🌐 *دستیاب ڈومینز*\n\n"
        for d in domains:
            msg += f"• `{d}`\n"
        await q.edit_message_text(msg, parse_mode="Markdown")

    # 🔹 CREATE EMAIL (USER‑WISE)
    elif q.data == "create":
        r = requests.get(f"{BASE_URL}/api/email/domains", headers=HEADERS)
        domain = r.json()["domains"][0]
        name = f"mudasir{random.randint(1000,9999)}"

        payload = {
            "name": name,
            "expiryTime": 3600000,
            "domain": domain
        }

        r = requests.post(f"{BASE_URL}/api/emails/generate", headers=HEADERS, json=payload)
        if r.status_code != 200:
            await q.edit_message_text("❌ ای میل بنانے میں مسئلہ آیا")
            return

        data = r.json()
        context.user_data.clear()
        context.user_data['email_id'] = data['id']
        context.user_data['email'] = data['email']

        keyboard = [
            [InlineKeyboardButton("📥 ان باکس دیکھیں", callback_data="inbox")],
            [InlineKeyboardButton("🌐 ڈومینز", callback_data="domains")]
        ]

        await q.edit_message_text(
            f"✅ *ای میل تیار ہے*\n\n📧 `{data['email']}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 🔹 INBOX (FILTERED – USER ONLY)
    elif q.data == "inbox":
        email_id = context.user_data.get('email_id')
        email_addr = context.user_data.get('email')

        if not email_id:
            await q.edit_message_text("❌ پہلے ای میل بنائیں")
            return

        r = requests.get(f"{BASE_URL}/api/emails", headers=HEADERS)
        emails = r.json().get("emails", [])

        msg = f"📥 *ان باکس* ({email_addr})\n\n"
        found = False
        for e in emails:
            if e['id'] == email_id:
                found = True
                msg += f"• موصول نہیں ہوئی ابھی\n"

        if not found:
            msg += "کوئی پیغام موجود نہیں"

        await q.edit_message_text(msg, parse_mode="Markdown")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(menu))

app.run_polling(drop_pending_updates=True)
