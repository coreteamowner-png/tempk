import os
import random
import string
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://api.mail.tm"

# ================== UTILS ==================

def gen_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 *MuDaSiR VIP Temp Mail Bot* 👑\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "> **✨ Yo hi mausam ki ada dekh kar yaad aaya**\n"
        "> **Faqat kaise badaltay hain log, jaan-e-jana 💔**\n>\n"
        "> **Tum bhi shayad isi mausam mein kahin kho gaye thay**\n"
        "> **Hum ne har simt tumhein dhoondha, magar paaya na gaya**\n>\n"
        "> — *Ahmad Faraz* 🌙\n\n"
        "🔐 Secure • Temporary • Private\n"
        "📥 Real Inbox • Live Refresh\n"
        "💎 Built for professionals"
    )

    keyboard = [
        [InlineKeyboardButton("✨ Create", callback_data="create"), InlineKeyboardButton("🌐 Domains", callback_data="domains")],
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox"), InlineKeyboardButton("✍️ Custom", callback_data="custom")]
    ],
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox")],
        [InlineKeyboardButton("✍️ Custom Email", callback_data="custom")],
    ]

    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================== CREATE EMAIL ==================
async def create_account(ctx, custom=None):
    domains = requests.get(f"{BASE_URL}/domains").json()["hydra:member"]
    domain = domains[0]["domain"]
    name = custom or f"mudasir{random.randint(1000,9999)}"
    email = f"{name}@{domain}"
    password = gen_password()

    acc = requests.post(f"{BASE_URL}/accounts", json={"address": email, "password": password})
    if acc.status_code not in (200, 201):
        return None

    token = requests.post(
        f"{BASE_URL}/token", json={"address": email, "password": password}
    ).json()["token"]

    headers = {"Authorization": f"Bearer {token}"}
    me = requests.get(f"{BASE_URL}/me", headers=headers).json()

    return {
        "email": email,
        "password": password,
        "token": token,
        "account_id": me["id"],
    }

# ================== INBOX ==================
async def show_inbox(message, context):
    token = context.user_data.get("token")
    if not token:
        await message.reply_text("❌ Please create an email first.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/messages", headers=headers)
    msgs = res.json().get("hydra:member", [])

    if not msgs:
        kb = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh")]]
        await message.reply_text("📭 Inbox is empty.", reply_markup=InlineKeyboardMarkup(kb))
        return

    buttons = []
    for m in msgs:
        label = f"📩 {m['subject'] or 'No Subject'}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"msg:{m['id']}")])

    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh")])

    await message.reply_text(
        "📥 *Inbox*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================== READ MESSAGE ==================
async def read_message(query, context, msg_id):
    token = context.user_data.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    m = requests.get(f"{BASE_URL}/messages/{msg_id}", headers=headers).json()

    text = (
        f"*From:* **{m['from']['address']}**\n"
        f"*Subject:* **{m['subject']}**\n\n"
        f"> {m.get('text', 'No content')}"
    )

    keyboard = [[InlineKeyboardButton("🔄 Refresh Inbox", callback_data="refresh")]]

    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== MENU HANDLER ==================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "create":
        data = await create_account(context)
        if not data:
            await q.message.reply_text("❌ Failed to create email")
            return
        context.user_data.clear()
        context.user_data.update(data)
        kb = [[InlineKeyboardButton("📥 Inbox", callback_data="inbox")]]
        await q.message.reply_text(f"✅ Email Created\n\n📧 `{data['email']}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "custom":
        context.user_data['await_custom'] = True
        await q.message.reply_text("✍️ Send custom email name")

    elif q.data == "inbox" or q.data == "refresh":
        await show_inbox(q.message, context)

    elif q.data.startswith("msg:"):
        await read_message(q, context, q.data.split(":")[1])

# ================== TEXT ==================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('await_custom'):
        context.user_data['await_custom'] = False
        data = await create_account(context, update.message.text.strip())
        if not data:
            await update.message.reply_text("❌ Failed to create email")
            return
        context.user_data.clear()
        context.user_data.update(data)
        kb = [[InlineKeyboardButton("📥 Inbox", callback_data="inbox")]]
        await update.message.reply_text(f"✅ Email Created\n\n📧 `{data['email']}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ================== RUN ==================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("inbox", lambda u, c: show_inbox(u.message, c)))
app.add_handler(CallbackQueryHandler(menu))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling(drop_pending_updates=True)
