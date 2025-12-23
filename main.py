import os
import random
import string
import re
import requests
from html import unescape
from bs4 import BeautifulSoup

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = "https://api.mail.tm"


# ---------------- HELPERS ----------------

PAK_GIRL_NAMES = [
    "Ayesha", "Fatima", "Zainab", "Hira", "Noor",
    "Iqra", "Maryam", "Sana", "Anaya", "Laiba"
]

JOHN_ELIA = (
    "❝\n"
    "یہ مجھے چین کیوں نہیں پڑتا\n"
    "ایک ہی شخص تھا جہاں میں کیا\n\n"
    "ہم نے مانا کہ تغافل نہ کرو گے، لیکن\n"
    "خاک ہو جائیں گے ہم، تم کو خبر ہونے تک\n"
    "❞"
)

def rand_digits(n: int) -> str:
    return "".join(random.choices(string.digits, k=n))

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "img"]):
        t.decompose()
    text = unescape(soup.get_text(separator="\n"))
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)

def extract_body(msg: dict) -> str:
    if msg.get("text"):
        return msg["text"]
    if msg.get("html"):
        return clean_html("\n".join(msg["html"]))
    return msg.get("intro", "")

def extract_otp(text: str):
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group(0) if m else None

def get_domains():
    r = requests.get(f"{BASE_URL}/domains", timeout=20)
    r.raise_for_status()
    return [d["domain"] for d in r.json()["hydra:member"]]

def create_account(email, password):
    r = requests.post(
        f"{BASE_URL}/accounts",
        json={"address": email, "password": password},
        timeout=20,
    )
    r.raise_for_status()

def get_token(email, password):
    r = requests.post(
        f"{BASE_URL}/token",
        json={"address": email, "password": password},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["token"]

def get_messages(token):
    r = requests.get(
        f"{BASE_URL}/messages",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json().get("hydra:member", [])

def get_message(token, mid):
    r = requests.get(
        f"{BASE_URL}/messages/{mid}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


# ---------------- COMMANDS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"🩷 *Assalamualaikum {user.first_name}*\n\n"
        f"*MuDaSiR VIP Temp Mail Bot*\n\n"
        f"{JOHN_ELIA}\n\n"
        "👇 *Choose an option*"
    )

    keyboard = [
        [
            InlineKeyboardButton("📧 Create Mail", callback_data="create"),
            InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
        ]
    ]

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🩷 *MuDaSiR VIP Temp Mail — Help*\n\n"
        "👨‍💻 Developer: *Mudasir*\n\n"
        "• Create Mail → Generates VIP email\n"
        "• Inbox → View received mails\n"
        "• OTP auto-detected\n"
        "• Full mail readable\n\n"
        "ℹ️ Telegram limitation: buttons cannot auto-copy.\n"
        "Long-press text to copy.\n\n"
        "✨ Enjoy VIP Experience ✨",
        parse_mode="Markdown",
    )


# ---------------- CALLBACKS ----------------

async def create_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    name = random.choice(PAK_GIRL_NAMES)
    username = (name.lower() + rand_digits(10))[:10]
    password = (name + "786$")[:12]
    domain = random.choice(get_domains())
    email = f"{username}@{domain}"

    create_account(email, password)
    token = get_token(email, password)

    # >>> STATE STORED HERE (FIXED ISSUE) <<<
    context.user_data["email"] = email
    context.user_data["password"] = password
    context.user_data["token"] = token

    text = (
        "💌 *EMAIL CREATED*\n\n"
        f"📧 *Email*\n`{email}`\n\n"
        f"📛 *Name*\n`{name}`\n\n"
        f"🔇 *Username*\n`{username}`\n\n"
        f"💻 *Password*\n`{password}`"
    )

    keyboard = [
        [
            InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
            InlineKeyboardButton("🔄 Refresh", callback_data="inbox"),
        ]
    ]

    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def open_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    token = context.user_data.get("token")
    if not token:
        await query.message.reply_text("❌ Create email first.")
        return

    mails = get_messages(token)
    if not mails:
        await query.message.reply_text("📭 Inbox empty.")
        return

    buttons = []
    for m in mails:
        subject = m.get("subject") or "No Subject"
        buttons.append([
            InlineKeyboardButton(subject[:40], callback_data=f"read:{m['id']}")
        ])

    buttons.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="inbox")
    ])

    await query.message.reply_text(
        "📥 *Inbox*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def read_mail(update: Update, context: ContextTypes.DEFAULT_TYPE, mid: str):
    query = update.callback_query

    token = context.user_data.get("token")
    if not token:
        await query.message.reply_text("❌ Session expired. Create mail again.")
        return

    msg = get_message(token, mid)
    body = extract_body(msg)
    otp = extract_otp(body)

    text = ""
    if otp:
        text += f"🔐 *Verification Code*\n`{otp}`\n\n"

    text += (
        f"📌 *Subject:* {msg.get('subject','')}\n"
        f"📧 *From:* {msg.get('from',{}).get('address','')}\n\n"
        f"```{body[:3500]}```"
    )

    await query.message.reply_text(text, parse_mode="Markdown")

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "create":
        await create_mail(update, context)
    elif data == "inbox":
        await open_inbox(update, context)
    elif data.startswith("read:"):
        await read_mail(update, context, data.split(":", 1)[1])


# ---------------- MAIN ----------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(callbacks))

    app.run_polling()

if __name__ == "__main__":
    main()
