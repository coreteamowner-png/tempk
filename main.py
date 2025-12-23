# ================================
# MuDaSiR VIP Mail.tm Telegram Bot
# FULL • CLEAN • WORKING • VIP UI
# ================================

import os
import random
import string
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================================
# CONFIG
# ================================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # set in Render
MAILTM_BASE = "https://api.mail.tm"

# ================================
# IN-MEMORY USER STORE
# ================================
# user_id -> {email, password, token, account_id}
USERS = {}

# ================================
# UTILITIES
# ================================
def rand_string(n=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def extract_readable_content(message: dict) -> str:
    # Prefer plain text
    if message.get("text") and message["text"].strip():
        return message["text"].strip()

    # HTML handling (array)
    html_blocks = message.get("html")
    if html_blocks:
        html = "\n".join(html_blocks)
        soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        text = soup.get_text(separator="\n")
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line and len(line) > 2:
                lines.append(line)
        cleaned = "\n".join(lines)
        if cleaned.strip():
            return cleaned.strip()

    # Fallback
    if message.get("intro"):
        return message["intro"]

    return "📭 No readable content found."


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


# ================================
# MAIL.TM API
# ================================
def get_domains():
    r = requests.get(f"{MAILTM_BASE}/domains")
    r.raise_for_status()
    data = r.json()
    return [d["domain"] for d in data.get("hydra:member", [])]


def create_account(address, password):
    r = requests.post(
        f"{MAILTM_BASE}/accounts",
        json={"address": address, "password": password},
    )
    r.raise_for_status()
    return r.json()


def get_token(address, password):
    r = requests.post(
        f"{MAILTM_BASE}/token",
        json={"address": address, "password": password},
    )
    r.raise_for_status()
    return r.json()["token"]


def get_messages(token):
    r = requests.get(
        f"{MAILTM_BASE}/messages",
        headers=auth_headers(token),
    )
    r.raise_for_status()
    return r.json().get("hydra:member", [])


def get_message(token, msg_id):
    r = requests.get(
        f"{MAILTM_BASE}/messages/{msg_id}",
        headers=auth_headers(token),
    )
    r.raise_for_status()
    return r.json()


# ================================
# BOT HANDLERS
# ================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🩷 *Welcome to MuDaSiR VIP Temp Mail* 🩷\n\n"
        "> _Yo hi mausam ki ada dekh kar yaad aaya hai_\n"
        "> _Faqat kaise badalte hain log, jaane jaana…_\n\n"
        "✨ Features:\n"
        "• Create temp email\n"
        "• Read OTP / HTML / Images\n"
        "• Inbox refresh\n\n"
        "👇 Choose an option"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💌 Create Email", callback_data="create"),
            InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
        ]
    ])
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🩷 *MuDaSiR VIP Help*\n\n"
        "Commands:\n"
        "/start – Open menu\n"
        "/create – Create email\n"
        "/inbox – View inbox\n\n"
        "Developer: *MuDaSiR*\n"
        "VIP Temp Mail Bot",
        parse_mode="Markdown"
    )


async def create_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    domains = get_domains()
    domain = random.choice(domains)

    name = f"mudasir_{rand_string(5)}"
    email = f"{name}@{domain}"
    password = rand_string(10)

    acc = create_account(email, password)
    token = get_token(email, password)

    USERS[user_id] = {
        "email": email,
        "password": password,
        "token": token,
        "account_id": acc["id"],
    }

    text = (
        f"🩷 *Email Created Successfully*\n\n"
        f"📧 `{email}`\n\n"
        "👇 Inbox open karo"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Open Inbox", callback_data="inbox")]
    ])

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.callback_query.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USERS:
        await update.callback_query.message.reply_text(
            "❌ Pehle email create karo."
        )
        return

    token = USERS[user_id]["token"]
    messages = get_messages(token)

    if not messages:
        await update.callback_query.message.reply_text("📭 Inbox empty hai.")
        return

    buttons = []
    for m in messages[:10]:
        subject = m.get("subject", "No Subject")
        buttons.append([
            InlineKeyboardButton(
                f"📨 {subject[:30]}",
                callback_data=f"read_{m['id']}"
            )
        ])

    await update.callback_query.message.reply_text(
        "📥 *Your Inbox*",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def read_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    msg_id = query.data.split("_", 1)[1]

    token = USERS[user_id]["token"]
    data = get_message(token, msg_id)

    sender = data["from"]["address"]
    subject = data.get("subject", "No Subject")
    body = extract_readable_content(data)

    text = (
        f"🩷 *From:* `{sender}`\n"
        f"💖 *Subject:* *{subject}*\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"```text\n{body[:3500]}\n```"
    )

    await query.message.reply_text(text, parse_mode="Markdown")


async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await inbox(update, context)


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    await update.callback_query.answer()

    if data == "create":
        await create_email(update, context)
    elif data == "inbox":
        await inbox(update, context)
    elif data == "refresh":
        await refresh(update, context)
    elif data.startswith("read_"):
        await read_mail(update, context)


# ================================
# MAIN
# ================================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("create", create_email))
    app.add_handler(CommandHandler("inbox", inbox))
    app.add_handler(CallbackQueryHandler(buttons))

    app.run_polling()


if __name__ == "__main__":
    main()
