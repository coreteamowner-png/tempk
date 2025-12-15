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

POETRY = [
    "*Tumhara gham hi to hai jo hame zinda rakhta hai*\n— *Jaun Elia*",
    "*Suna hai log use aankhon mein basate hain*\n— *Ahmad Faraz*",
    "*Main bhi bohot ajeeb hoon, itna ajeeb hoon ke bas*\n— *Jaun Elia*",
    "*Ranjish hi sahi dil hi dukhane ke liye aa*\n— *Ahmad Faraz*",
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        "👑 *MuDaSiR VIP Temp Mail Bot* 👑\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{random.choice(POETRY)}\n\n"
        f"Welcome {user.mention_markdown_v2()} 🌹"
    )

    keyboard = [
        [InlineKeyboardButton("✨ Create Temp Mail", callback_data="create")],
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox")],
        [InlineKeyboardButton("🌐 Domains", callback_data="domains")],
        [InlineKeyboardButton("🗑 Delete Email", callback_data="delete")],
    ]

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "domains":
        r = requests.get(f"{BASE_URL}/api/email/domains", headers=HEADERS)
        domains = r.json().get("domains", [])
        msg = "🌐 *Available Domains*\n\n"
        for d in domains:
            msg += f"• `{d}`\n"
        await q.edit_message_text(msg, parse_mode="Markdown")

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
            await q.edit_message_text("❌ Email creation failed")
            return

        data = r.json()
        context.user_data['email_id'] = data['id']
        context.user_data['email'] = data['email']

        await q.edit_message_text(
            f"✅ *Email Created*\n\n📧 `{data['email']}`",
            parse_mode="Markdown"
        )

    elif q.data == "inbox":
        r = requests.get(f"{BASE_URL}/api/emails", headers=HEADERS)
        emails = r.json().get("emails", [])
        if not emails:
            await q.edit_message_text("📭 Inbox empty")
            return

        msg = "📥 *Your Emails*\n\n"
        for e in emails:
            msg += f"• `{e['address']}`\n"
        await q.edit_message_text(msg, parse_mode="Markdown")

    elif q.data == "delete":
        email_id = context.user_data.get('email_id')
        if not email_id:
            await q.edit_message_text("❌ No email to delete")
            return

        r = requests.delete(f"{BASE_URL}/api/emails/{email_id}", headers=HEADERS)
        if r.status_code == 200:
            context.user_data.clear()
            await q.edit_message_text("🗑 Email deleted successfully")
        else:
            await q.edit_message_text("❌ Delete failed")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(menu))

app.run_polling(drop_pending_updates=True)
