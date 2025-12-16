import os
import random
import string
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://api.mail.tm"

# ========== HELPERS ==========

def rand_pass():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 MuDaSiR VIP Temp Mail Bot 👑\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Wo hi mausam ki ada thi shayad\n"
        "Jis ne seene mein jalan paida ki\n\n"
        "Main ne samjha tha ke tu hai to nahi\n"
        "Phir ye kyun dil mein kasak paida ki\n\n"
        "Ranjish hi sahi dil hi dukhane ke liye aa\n"
        "Aa phir se mujhe chhor ke jaane ke liye aa\n"
        "— Ahmad Faraz\n\n"
        "✨ Create secure temporary emails\n"
        "📥 Read real inbox messages\n"
        "💎 Fully private & user‑isolated"
    )

    kb = [
        [InlineKeyboardButton("✨ Create Email", callback_data="create")],
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox")],
        [InlineKeyboardButton("✍️ Custom Email", callback_data="custom")],
        [InlineKeyboardButton("🗑 Delete Email", callback_data="delete")]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ========== CREATE ACCOUNT ==========
async def create_email(query, context, custom=None):
    domains = requests.get(f"{BASE_URL}/domains").json()['hydra:member']
    domain = domains[0]['domain']
    name = custom or f"mudasir{random.randint(1000,9999)}"
    email = f"{name}@{domain}"
    password = rand_pass()

    acc = requests.post(f"{BASE_URL}/accounts", json={"address": email, "password": password})
    if acc.status_code not in (200, 201):
        await query.message.reply_text("❌ Failed to create email")
        return

    token = requests.post(f"{BASE_URL}/token", json={"address": email, "password": password}).json()['token']

    context.user_data.clear()
    context.user_data.update({
        "email": email,
        "password": password,
        "token": token
    })

    headers = {"Authorization": f"Bearer {token}"}
    me = requests.get(f"{BASE_URL}/me", headers=headers).json()
    context.user_data['account_id'] = me['id']

    kb = [[InlineKeyboardButton("📥 Inbox", callback_data="inbox")]]
    await query.message.reply_text(f"✅ Email Created\n\n📧 {email}", reply_markup=InlineKeyboardMarkup(kb))

# ========== INBOX ==========
async def inbox(update, context):
    token = context.user_data.get('token')
    if not token:
        await update.message.reply_text("❌ Create an email first")
        return

    headers = {"Authorization": f"Bearer {token}"}
    msgs = requests.get(f"{BASE_URL}/messages", headers=headers).json()['hydra:member']

    if not msgs:
        await update.message.reply_text("📭 Inbox empty")
        return

    kb = []
    for m in msgs:
        kb.append([InlineKeyboardButton(m['subject'] or "(No subject)", callback_data=f"msg:{m['id']}")])

    await update.message.reply_text("📥 Inbox", reply_markup=InlineKeyboardMarkup(kb))

# ========== READ MESSAGE ==========
async def read_message(query, context, msg_id):
    token = context.user_data.get('token')
    headers = {"Authorization": f"Bearer {token}"}
    m = requests.get(f"{BASE_URL}/messages/{msg_id}", headers=headers).json()

    text = (
        f"From: {m['from']['address']}\n"
        f"Subject: {m['subject']}\n\n"
        f"{m.get('text','')[:3500]}"
    )

    await query.message.reply_text(text)

# ========== MENU ==========
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "create":
        await create_email(q, context)

    elif q.data == "custom":
        context.user_data['await_name'] = True
        await q.message.reply_text("✍️ Send custom email name")

    elif q.data == "inbox":
        await inbox(q.message, context)

    elif q.data.startswith("msg:"):
        await read_message(q, context, q.data.split(":")[1])

    elif q.data == "delete":
        token = context.user_data.get('token')
        acc_id = context.user_data.get('account_id')
        if token and acc_id:
            requests.delete(f"{BASE_URL}/accounts/{acc_id}", headers={"Authorization": f"Bearer {token}"})
        context.user_data.clear()
        await q.message.reply_text("🗑 Email deleted")

# ========== TEXT HANDLER ==========
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('await_name'):
        context.user_data['await_name'] = False
        await create_email(update, context, update.message.text.strip())

# ========== RUN ==========
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("inbox", inbox))
app.add_handler(CallbackQueryHandler(menu))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling(drop_pending_updates=True)
