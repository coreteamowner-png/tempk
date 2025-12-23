import os
import random
import string
import re
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
MAILTM_BASE = "https://api.mail.tm"

USERS = {}

def rand_digits(n):
    return "".join(random.choices(string.digits, k=n))

def strong_password():
    return f"Malik{rand_digits(4)}$"

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}

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

def get_messages(token):
    r = requests.get(f"{MAILTM_BASE}/messages", headers=auth_headers(token))
    r.raise_for_status()
    return r.json().get("hydra:member", [])

def get_message(token, mid):
    r = requests.get(f"{MAILTM_BASE}/messages/{mid}", headers=auth_headers(token))
    r.raise_for_status()
    return r.json()

def clean_html(html_blocks):
    soup = BeautifulSoup("\n".join(html_blocks), "html.parser")
    for t in soup(["script", "style", "noscript", "img"]):
        t.decompose()
    text = soup.get_text("\n")
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
        return msg["text"]
    if msg.get("html"):
        return clean_html(msg["html"])
    return msg.get("intro", "")

def find_otp(text):
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group(0) if m else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💌 Create Email", callback_data="create"),
            InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
        ]
    ])
    await update.message.reply_text(
        "🩷 *MuDaSiR VIP Temp Mail*\n\n"
        "> _Yo hi mausam ki ada dekh kar yaad aaya hai_\n"
        "> _Faqat kaise badalte hain log, jaane jaana…_\n\n"
        "👇 Choose option",
        parse_mode="Markdown",
        reply_markup=kb
    )

async def create_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    domains = get_domains()
    domain = random.choice(domains)
    username = f"mudasir_{rand_digits(10)}"
    email = f"{username}@{domain}"
    password = strong_password()
    acc = create_account(email, password)
    token = get_token(email, password)

    USERS[uid] = {
        "email": email,
        "password": password,
        "token": token,
        "account_id": acc["id"],
    }

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Copy Email", callback_data="copy_email")],
        [InlineKeyboardButton("📋 Copy Password", callback_data="copy_pass")],
        [InlineKeyboardButton("📥 Open Inbox", callback_data="inbox")],
    ])

    await update.callback_query.message.reply_text(
        f"🩷 *Email Created*\n\n"
        f"📧 `{email}`\n"
        f"🔑 `{password}`",
        parse_mode="Markdown",
        reply_markup=kb
    )

async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in USERS:
        await update.callback_query.message.reply_text("❌ Create email first.")
        return
    msgs = get_messages(USERS[uid]["token"])
    if not msgs:
        await update.callback_query.message.reply_text("📭 Inbox empty.")
        return
    buttons = []
    for m in msgs[:10]:
        sub = m.get("subject", "No Subject")
        buttons.append([InlineKeyboardButton(sub[:30], callback_data=f"read_{m['id']}")])
    await update.callback_query.message.reply_text(
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
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Copy OTP", callback_data=f"copy_otp_{otp}")],
            [InlineKeyboardButton("📄 View Full Mail", callback_data=f"full_{mid}")]
        ])
        await q.message.reply_text(
            f"🔐 *Verification Code*\n\n"
            f"`{otp}`",
            parse_mode="Markdown",
            reply_markup=kb
        )
    else:
        await q.message.reply_text(
            f"*{msg.get('subject','No Subject')}*\n\n```text\n{body[:3500]}\n```",
            parse_mode="Markdown"
        )

async def full_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    mid = q.data.split("_", 1)[1]
    msg = get_message(USERS[uid]["token"], mid)
    body = extract_body(msg)
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
    elif d.startswith("full_"):
        await full_mail(update, context)
    elif d == "copy_email":
        await q.message.reply_text(USERS[q.from_user.id]["email"])
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
