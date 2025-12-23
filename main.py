import os
import random
import string
import re
import requests
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
MAILTM_BASE = "https://api.mail.tm"

USERS = {}

PAK_GIRL_NAMES = [
    "Ayesha","Fatima","Zainab","Hira","Noor","Iqra","Maryam",
    "Laiba","Eman","Sana","Anaya","Areeba","Mahnoor","Alina"
]

JOHN_ELIA_SHAYARI = [
    "یہ مجھے چین کیوں نہیں پڑتا\nایک ہی شخص تھا جہاں میں کیا",
    "بہت قریب آتی جا رہی ہو\nبچھڑنے کا ارادہ تو نہیں ہے",
    "عجیب سا حق ہے تم پر\nکہ تمہاری خاموشی بھی گفتگو لگتی ہے",
]

def rand_digits(n):
    return "".join(random.choices(string.digits, k=n))

def get_domains():
    r = requests.get(f"{MAILTM_BASE}/domains")
    r.raise_for_status()
    return [d["domain"] for d in r.json().get("hydra:member", [])]

def create_account(address, password):
    r = requests.post(f"{MAILTM_BASE}/accounts", json={"address": address, "password": password})
    r.raise_for_status()
    return r.json()

def get_token(address, password):
    r = requests.post(f"{MAILTM_BASE}/token", json={"address": address, "password": password})
    r.raise_for_status()
    return r.json()["token"]

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

def get_messages(token):
    r = requests.get(f"{MAILTM_BASE}/messages", headers=auth_headers(token))
    r.raise_for_status()
    return r.json().get("hydra:member", [])

def get_message(token, mid):
    r = requests.get(f"{MAILTM_BASE}/messages/{mid}", headers=auth_headers(token))
    r.raise_for_status()
    return r.json()

def clean_text(text):
    text = unescape(text)
    lines = []
    for l in text.splitlines():
        l = l.strip()
        if not l:
            continue
        if l.startswith("http"):
            continue
        if "unsubscribe" in l.lower():
            continue
        lines.append(l)
    return "\n".join(lines)

def extract_body(msg):
    if msg.get("text"):
        return clean_text(msg["text"])
    if msg.get("html"):
        return clean_text(" ".join(msg["html"]))
    return clean_text(msg.get("intro", ""))

def find_otp(text):
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group(0) if m else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shayr = random.choice(JOHN_ELIA_SHAYARI)
    await update.message.reply_text(
        f"🩷 *MuDaSiR VIP Temp Mail*\n\n"
        f"Assalamualaikum {update.effective_user.mention_html()}\n\n"
        f"〝{shayr}〞\n\n"
        f"👇 Choose Option",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✉️ Create Mail", callback_data="create"),
                InlineKeyboardButton("📥 Inbox", callback_data="inbox")
            ]
        ])
    )

async def create_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id

    name = random.choice(PAK_GIRL_NAMES)
    username = (name.lower() + rand_digits(10))[:10]
    password = (name + "786$")[:12]

    domain = random.choice(get_domains())
    email = f"{username}@{domain}"

    acc = create_account(email, password)
    token = get_token(email, password)

    USERS[uid] = {
        "email": email,
        "password": password,
        "username": username,
        "name": name,
        "token": token,
        "account_id": acc["id"],
    }

    text = (
        "💌 *EMAIL CREATED*\n\n"
        f"📧 *Email:* `{email}`\n"
        f"📛 *Name:* `{name}`\n"
        f"🔇 *Username:* `{username}`\n"
        f"💻 *Password:* `{password}`"
    )

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✉️ Copy Email", callback_data="copy_email"),
            InlineKeyboardButton("📛 Copy Name", callback_data="copy_name")
        ],
        [
            InlineKeyboardButton("🔇 Copy Username", callback_data="copy_user"),
            InlineKeyboardButton("💻 Copy Password", callback_data="copy_pass")
        ],
        [
            InlineKeyboardButton("📥 Open Inbox", callback_data="inbox")
        ]
    ])

    await q.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    if uid not in USERS:
        await q.message.reply_text("❌ Create email first.")
        return

    msgs = get_messages(USERS[uid]["token"])
    if not msgs:
        await q.message.reply_text("📭 Inbox empty.")
        return

    buttons = []
    for m in msgs[:10]:
        buttons.append([
            InlineKeyboardButton(
                f"📨 {m.get('subject','No Subject')[:30]}",
                callback_data=f"read_{m['id']}"
            )
        ])

    await q.message.reply_text(
        "📥 *Inbox*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def read_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    mid = q.data.split("_", 1)[1]

    msg = get_message(USERS[uid]["token"], mid)
    body = extract_body(msg)
    otp = find_otp(body)

    if otp:
        await q.message.reply_text(
            f"🔐 *Verification Code*\n\n`{otp}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Copy OTP", callback_data=f"copy_otp_{otp}")]
            ])
        )
    else:
        await q.message.reply_text(
            f"*{msg.get('subject','No Subject')}*\n\n```text\n{body[:3500]}\n```",
            parse_mode="Markdown"
        )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "create":
        await create_email(update, context)
    elif d == "inbox":
        await inbox(update, context)
    elif d.startswith("read_"):
        await read_mail(update, context)
    elif d == "copy_email":
        await q.message.reply_text(USERS[q.from_user.id]["email"])
    elif d == "copy_name":
        await q.message.reply_text(USERS[q.from_user.id]["name"])
    elif d == "copy_user":
        await q.message.reply_text(USERS[q.from_user.id]["username"])
    elif d == "copy_pass":
        await q.message.reply_text(USERS[q.from_user.id]["password"])
    elif d.startswith("copy_otp_"):
        await q.message.reply_text(d.replace("copy_otp_", ""))

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()

if __name__ == "__main__":
    main()
