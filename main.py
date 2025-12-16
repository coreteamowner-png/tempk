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

WELCOME_POETRY = (
"Ye bhi kya shaam-e-mulaqat aayi\n"
"Lab pe mehki hui baat aayi\n\n"
"Wo hi mausam ki ada thi shayad\n"
"Jis ne seene mein jalan aayi\n\n"
"Ranjish hi sahi dil hi dukhane ke liye aa\n"
"Aa phir se mujhe chhor ke jaane ke liye aa\n"
"— Ahmad Faraz"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        "👑 MuDaSiR VIP Temp Mail Bot 👑\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{WELCOME_POETRY}\n\n"
        f"Welcome {user.first_name}! 💎\n"
        "Create secure temp emails instantly.\n"
        "No spam • No signup • Fully private"
    )

    keyboard = [
        [InlineKeyboardButton("✨ Create Email", callback_data="create")],
        [InlineKeyboardButton("✍️ Custom Email", callback_data="custom")],
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox")],
        [InlineKeyboardButton("🌐 Domains", callback_data="domains")],
        [InlineKeyboardButton("🗑 Delete Email", callback_data="delete")],
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def inbox_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_inbox(update.message, context)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "domains":
        r = requests.get(f"{BASE_URL}/api/email/domains", headers=HEADERS)
        domains = r.json().get("domains", [])
        msg = "🌐 Available Domains\n\n" + "\n".join(domains)
        await q.edit_message_text(msg)

    elif q.data == "create":
        await create_email(q, context)

    elif q.data == "custom":
        context.user_data['await_name'] = True
        await q.edit_message_text("✍️ Send custom email name (text only)")

    elif q.data == "inbox":
        await show_inbox(q.message, context)

    elif q.data == "delete":
        email_id = context.user_data.get('email_id')
        if not email_id:
            await q.edit_message_text("❌ No email to delete")
            return
        requests.delete(f"{BASE_URL}/api/emails/{email_id}", headers=HEADERS)
        context.user_data.clear()
        await q.edit_message_text("🗑 Email deleted successfully")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('await_name'):
        name = update.message.text.strip()
        context.user_data['await_name'] = False
        await create_email(update.message, context, name)

async def create_email(msg_obj, context, name=None):
    r = requests.get(f"{BASE_URL}/api/email/domains", headers=HEADERS)
    domain = r.json()["domains"][0]
    if not name:
        name = f"mudasir{random.randint(1000,9999)}"

    payload = {
        "name": name,
        "expiryTime": 3600000,
        "domain": domain
    }

    r = requests.post(f"{BASE_URL}/api/emails/generate", headers=HEADERS, json=payload)
    if r.status_code != 200:
        await msg_obj.reply_text("❌ Failed to create email")
        return

    data = r.json()
    context.user_data['email_id'] = data['id']
    context.user_data['email'] = data['email']

    keyboard = [
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox")],
        [InlineKeyboardButton("🗑 Delete", callback_data="delete")]
    ]

    await msg_obj.reply_text(
        f"✅ Email Created Successfully\n\n📧 {data['email']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_inbox(msg_obj, context):
    email = context.user_data.get('email')
    if not email:
        await msg_obj.reply_text("❌ No email created yet")
        return

    await msg_obj.reply_text(
        f"📥 Inbox Status\n\n"
        f"Email: {email}\n"
        f"Status: Active ✅\n\n"
        "⚠️ Message content is not accessible via API"
    )

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("inbox", inbox_cmd))
app.add_handler(CallbackQueryHandler(menu))
app.add_handler(CommandHandler("text", text_handler))

app.run_polling(drop_pending_updates=True)
