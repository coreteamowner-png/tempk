import os
import random
import string
import re
import requests
from bs4 import BeautifulSoup
from html import unescape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://api.mail.tm"

# =========================
# USER STORAGE (IMPORTANT)
# =========================
USERS = {}  # user_id -> dict(email, token, password)

# =========================
# HELPERS
# =========================

PAK_GIRL_NAMES = [
    "Ayesha","Fatima","Zainab","Hira","Noor",
    "Iqra","Maryam","Sana","Anaya","Laiba"
]

JOHN_ELIA_SHAYARI = (
    "❝\n"
    "یہ مجھے چین کیوں نہیں پڑتا\n"
    "ایک ہی شخص تھا جہاں میں کیا\n\n"
    "ہم نے مانا کہ تغافل نہ کرو گے، لیکن\n"
    "خاک ہو جائیں گے ہم، تم کو خبر ہونے تک\n"
    "❞"
)

def rand_digits(n):
    return "".join(random.choices(string.digits, k=n))

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "img"]):
        t.decompose()
    text = soup.get_text(separator="\n")
    text = unescape(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)

def extract_body(msg):
    if msg.get("text"):
        return msg["text"]
    if msg.get("html"):
        return clean_html("\n".join(msg["html"]))
    return msg.get("intro", "")

def extract_otp(text):
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group(0) if m else None

def get_domains():
    r = requests.get(f"{BASE_URL}/domains")
    r.raise_for_status()
    return [d["domain"] for d in r.json()["hydra:member"]]

def create_account(email, password):
    r = requests.post(
        f"{BASE_URL}/accounts",
        json={"address": email, "password": password}
    )
    r.raise_for_status()

def get_token(email, password):
    r = requests.post(
        f"{BASE_URL}/token",
        json={"address": email, "password": password}
    )
    r.raise_for_status()
    return r.json()["token"]

def get_messages(token):
    return requests.get(
        f"{BASE_URL}/messages",
        headers={"Authorization": f"Bearer {token}"}
    ).json().get("hydra:member", [])

def get_message(token, mid):
    return requests.get(
        f"{BASE_URL}/messages/{mid}",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

# =========================
# COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    text = (
        f"🩷 *Assalamualaikum {user.first_name}*\n\n"
        f"*MuDaSiR VIP Temp Mail Bot*\n\n"
        f"{JOHN_ELIA_SHAYARI}\n\n"
        "👇 *Select an option*"
    )

    keyboard = [
        [InlineKeyboardButton("📧 Create Mail", callback_data="create")],
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox")]
    ]

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🩷 *MuDaSiR VIP Temp Mail — Help*\n\n"
        "👨‍💻 Developer: *Mudasir*\n\n"
        "1️⃣ Create Mail\n"
        "2️⃣ Open Inbox\n"
        "3️⃣ OTP auto detected\n"
        "4️⃣ View full mail anytime\n\n"
        "ℹ️ Long-press text to copy\n"
        "✨ VIP Experience ✨",
        parse_mode="Markdown"
    )

# =========================
# CORE LOGIC
# =========================

async def handle_create(update, context):
    query = update.callback_query
    uid = query.from_user.id

    name = random.choice(PAK_GIRL_NAMES)
    username = (name.lower() + rand_digits(10))[:10]
    password = (name + "786$")[:12]
    domain = random.choice(get_domains())

    email = f"{username}@{domain}"

    create_account(email, password)
    token = get_token(email, password)

    USERS[uid] = {
        "email": email,
        "password": password,
        "token": token
    }

    text = (
        "💌 *EMAIL CREATED*\n\n"
        f"📧 `{email}`\n"
        f"📛 `{name}`\n"
        f"🔇 `{username}`\n"
        f"💻 `{password}`"
    )

    keyboard = [
        [InlineKeyboardButton("📥 Open Inbox", callback_data="inbox")]
    ]

    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_inbox(update, context):
    query = update.callback_query
    uid = query.from_user.id

    if uid not in USERS:
        await query.message.reply_text("❌ Create mail first.")
        return

    token = USERS[uid]["token"]
    msgs = get_messages(token)

    if not msgs:
        await query.message.reply_text("📭 Inbox empty.")
        return

    buttons = []
    for m in msgs:
        subject = m.get("subject") or "No Subject"
        buttons.append([
            InlineKeyboardButton(subject[:40], callback_data=f"read:{m['id']}")
        ])

    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="inbox")])

    await query.message.reply_text(
        "📥 *Inbox*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def handle_read(update, context, mid):
    query = update.callback_query
    uid = query.from_user.id

    token = USERS[uid]["token"]
    msg = get_message(token, mid)

    body = extract_body(msg)
    otp = extract_otp(body)

    if otp:
        text = (
            "🔐 *Verification Code*\n\n"
            f"`{otp}`\n\n"
            "_Full mail below_"
        )
    else:
        text = ""

    text += (
        f"\n\n📌 *Subject:* {msg.get('subject','')}\n"
        f"📧 *From:* {msg.get('from',{}).get('address','')}\n\n"
        f"```{body[:3500]}```"
    )

    await query.message.reply_text(text, parse_mode="Markdown")

# =========================
# CALLBACK ROUTER
# =========================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "create":
        await handle_create(update, context)
    elif data == "inbox":
        await handle_inbox(update, context)
    elif data.startswith("read:"):
        await handle_read(update, context, data.split(":",1)[1])

# =========================
# MAIN
# =========================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.run_polling()

if __name__ == "__main__":
    main()
