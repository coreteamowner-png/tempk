import os
import random
import string
import requests
import re
from bs4 import BeautifulSoup
from html import unescape

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

BOT_TOKEN = os.getenv("BOT_TOKEN")

BASE_URL = "https://api.mail.tm"

users = {}  # user_id -> account data


# ---------- HELPERS ----------

def random_name():
    pak_girls = [
        "Ayesha", "Hira", "Fatima", "Zainab", "Iqra",
        "Sana", "Noor", "Laiba", "Maryam", "Anaya"
    ]
    return random.choice(pak_girls)


def generate_username(name):
    digits = ''.join(random.choices(string.digits, k=6))
    return (name.lower() + digits)[:10]


def generate_password(name):
    base = f"{name}786$"
    return base[:12]


def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    text = unescape(text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_otp(text):
    match = re.search(r"\b(\d{4,8})\b", text)
    return match.group(1) if match else None


# ---------- COMMANDS ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    shayari = (
        "❝\n"
        "یہ مجھے چین کیوں نہیں پڑتا\n"
        "ایک ہی شخص تھا جہاں میں کیا\n\n"
        "ہم نے مانا کہ تغافل نہ کرو گے، لیکن\n"
        "خاک ہو جائیں گے ہم، تم کو خبر ہونے تک\n"
        "❞"
    )

    text = (
        f"🩷 *Assalamualaikum {user.mention_html()}*\n\n"
        f"*MuDaSiR VIP Temp Mail Bot*\n\n"
        f"{shayari}\n\n"
        "👇 *Click below to create your VIP email*"
    )

    keyboard = [
        [InlineKeyboardButton("📧 Create Email", callback_data="create")]
    ]

    await update.message.reply_html(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🩷 *MuDaSiR VIP Temp Mail — Help*\n\n"
        "👨‍💻 Developer: *Mudasir*\n\n"
        "📌 *Commands*\n"
        "/start – Start bot\n"
        "/help – Full guide\n\n"
        "🛠 *How to use*\n"
        "1️⃣ Create Email\n"
        "2️⃣ Open Inbox\n"
        "3️⃣ OTP auto detected\n"
        "4️⃣ View full email anytime\n\n"
        "ℹ️ Telegram bots cannot auto-copy.\n"
        "Long-press text to copy.\n\n"
        "✨ Enjoy VIP experience ✨"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


# ---------- CALLBACKS ----------

async def create_email(query, user_id):
    name = random_name()
    username = generate_username(name)
    password = generate_password(name)

    domains = requests.get(f"{BASE_URL}/domains").json()["hydra:member"]
    domain = domains[0]["domain"]

    address = f"{username}@{domain}"

    res = requests.post(
        f"{BASE_URL}/accounts",
        json={"address": address, "password": password},
    )

    if res.status_code not in (200, 201):
        await query.message.reply_text("❌ Failed to create email")
        return

    token = requests.post(
        f"{BASE_URL}/token",
        json={"address": address, "password": password},
    ).json()["token"]

    users[user_id] = {
        "address": address,
        "password": password,
        "token": token,
    }

    text = (
        "💌 *EMAIL CREATED*\n\n"
        f"📧 *Email:*\n`{address}`\n\n"
        f"📛 *Name:*\n`{name}`\n\n"
        f"🔇 *Username:*\n`{username}`\n\n"
        f"💻 *Password:*\n`{password}`"
    )

    keyboard = [
        [InlineKeyboardButton("📥 Inbox", callback_data="inbox")]
    ]

    await query.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def inbox(query, user_id):
    if user_id not in users:
        await query.message.reply_text("❌ Create email first")
        return

    token = users[user_id]["token"]

    headers = {"Authorization": f"Bearer {token}"}
    msgs = requests.get(f"{BASE_URL}/messages", headers=headers).json()

    mails = msgs.get("hydra:member", [])
    if not mails:
        await query.message.reply_text("📭 Inbox empty")
        return

    buttons = []
    for m in mails:
        subject = m["subject"] or "No Subject"
        buttons.append([
            InlineKeyboardButton(subject[:40], callback_data=f"mail:{m['id']}")
        ])

    buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="inbox")])

    await query.message.reply_text(
        "📨 *Inbox*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def read_mail(query, user_id, mail_id):
    token = users[user_id]["token"]
    headers = {"Authorization": f"Bearer {token}"}

    mail = requests.get(
        f"{BASE_URL}/messages/{mail_id}", headers=headers
    ).json()

    subject = mail.get("subject", "No Subject")
    sender = mail.get("from", {}).get("address", "Unknown")

    body = ""
    if mail.get("html"):
        body = clean_html(mail["html"][0])
    else:
        body = mail.get("text", "")

    otp = extract_otp(body)

    if otp:
        text = (
            "🔐 *OTP DETECTED*\n\n"
            f"`{otp}`\n\n"
            "👇 Full mail below"
        )
    else:
        text = ""

    text += (
        "\n\n"
        f"📌 *Subject:* {subject}\n"
        f"📧 *From:* {sender}\n\n"
        f"```{body[:3500]}```"
    )

    await query.message.reply_text(text, parse_mode="Markdown")


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data == "create":
        await create_email(query, user_id)

    elif data == "inbox":
        await inbox(query, user_id)

    elif data.startswith("mail:"):
        mail_id = data.split(":", 1)[1]
        await read_mail(query, user_id, mail_id)


# ---------- MAIN ----------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(callbacks))

    app.run_polling()


if __name__ == "__main__":
    main()
