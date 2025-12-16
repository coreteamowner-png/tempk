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

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://api.mail.tm"

# ================= HELPERS =================

def gen_password(length: int = 12) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 *MuDaSiR VIP Temp Mail Bot* 👑\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "> 🌙 **Yo hi mausam ki ada dekh kar yaad aaya**\n"
        "> **Faqat kaise badaltay hain log, jaan-e-jana**\n>\n"
        "> **Tum bhi shayad isi mausam mein kahin kho gaye thay**\n"
        "> **Hum ne har simt tumhein dhoondha, magar paaya na gaya**\n>\n"
        "> — *Ahmad Faraz* ✨\n\n"
        "🔐 Secure • Temporary • Private\n"
        "📥 Real Inbox • 🔄 Refresh Enabled"
    )

    keyboard = [
        [InlineKeyboardButton("✨ Create", callback_data="create"), InlineKeyboardButton("🌐 Domains", callback_data="domains")],
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox"), InlineKeyboardButton("✍️ Custom", callback_data="custom")],
    ]

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ================= DOMAIN LIST =================
async def show_domains(message, context):
    # Fetch MULTIPLE pages to get more domains (Mail.tm paginated)
    all_domains = []
    for page in range(1, 4):  # first 3 pages = enough
        res = requests.get(f"{BASE_URL}/domains?page={page}")
        data = res.json().get("hydra:member", [])
        if not data:
            break
        all_domains.extend(data)

    if not all_domains:
        await message.reply_text("❌ No domains available right now")
        return

    buttons = []
    for d in all_domains[:12]:  # limit buttons
        buttons.append([InlineKeyboardButton(d["domain"], callback_data=f"dom:{d['domain']}")])

    await message.reply_text(
        "🌐 *Select a domain (VIP)*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ================= CREATE ACCOUNT =================
async def create_account(context, name=None, domain=None):
    # choose domain
    if not domain:
        res = requests.get(f"{BASE_URL}/domains")
        domain = res.json()["hydra:member"][0]["domain"]

    username = name or f"mudasir{random.randint(1000,9999)}"
    email = f"{username}@{domain}"
    password = gen_password()

    acc = requests.post(
        f"{BASE_URL}/accounts",
        json={"address": email, "password": password},
    )
    if acc.status_code not in (200, 201):
        return None

    tok = requests.post(
        f"{BASE_URL}/token",
        json={"address": email, "password": password},
    ).json().get("token")

    headers = {"Authorization": f"Bearer {tok}"}
    me = requests.get(f"{BASE_URL}/me", headers=headers).json()

    return {
        "email": email,
        "password": password,
        "token": tok,
        "account_id": me.get("id"),
    }

# ================= INBOX =================
async def show_inbox(message, context):
    token = context.user_data.get("token")
    if not token:
        await message.reply_text("❌ Please create an email first")
        return

    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(f"{BASE_URL}/messages", headers=headers)
    msgs = res.json().get("hydra:member", [])

    if not msgs:
        kb = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh")]]
        await message.reply_text("📭 Inbox is empty", reply_markup=InlineKeyboardMarkup(kb))
        return

    buttons = []
    for m in msgs:
        subject = m.get("subject") or "(No Subject)"
        buttons.append([InlineKeyboardButton(f"📩 {subject}", callback_data=f"msg:{m['id']}")])

    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh")])

    await message.reply_text("📥 *Inbox*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

# ================= READ MESSAGE =================
async def read_message(query, context, msg_id):
    token = context.user_data.get("token")
    headers = {"Authorization": f"Bearer {token}"}
    m = requests.get(f"{BASE_URL}/messages/{msg_id}", headers=headers).json()

    sender = m.get("from", {}).get("address", "")
    subject = m.get("subject", "")
    body = m.get("text", "No content")

    text = (
        f"*From:* **{sender}**\n"
        f"*Subject:* **{subject}**\n\n"
        f"> {body}"
    )

    kb = [[InlineKeyboardButton("🔄 Refresh Inbox", callback_data="refresh")]]

    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ================= MENU HANDLER =================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "create":
        domain = context.user_data.get("selected_domain")
        data = await create_account(context, domain=domain)
        if not data:
            await q.message.reply_text("❌ Failed to create email")
            return
        context.user_data.clear()
        context.user_data.update(data)
        kb = [[InlineKeyboardButton("📥 Inbox", callback_data="inbox")]]
        await q.message.reply_text(f"✅ Email Created\n\n📧 `{data['email']}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "domains":
        await show_domains(q.message, context)

    elif q.data.startswith("dom:"):
        context.user_data["selected_domain"] = q.data.split(":", 1)[1]
        await q.message.reply_text(f"✅ Domain selected: {context.user_data['selected_domain']}")

    elif q.data == "custom":
        context.user_data["await_custom"] = True
        await q.message.reply_text("✍️ Send custom email name (only text)")

    elif q.data in ("inbox", "refresh"):
        await show_inbox(q.message, context)

    elif q.data.startswith("msg:"):
        await read_message(q, context, q.data.split(":", 1)[1])

# ================= TEXT HANDLER =================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("await_custom"):
        context.user_data["await_custom"] = False
        name = update.message.text.strip()
        domain = context.user_data.get("selected_domain")
        data = await create_account(context, name=name, domain=domain)
        if not data:
            await update.message.reply_text("❌ Failed to create email")
            return
        context.user_data.clear()
        context.user_data.update(data)
        kb = [[InlineKeyboardButton("📥 Inbox", callback_data="inbox")]]
        await update.message.reply_text(f"✅ Email Created\n\n📧 `{data['email']}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("inbox", lambda u, c: show_inbox(u.message, c)))
app.add_handler(CallbackQueryHandler(menu))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling(drop_pending_updates=True)
