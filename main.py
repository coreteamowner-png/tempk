import os
import random
import string
import asyncio
import re
from html import unescape

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

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BASE_URL = "https://api.mail.tm"
MAX_LEN = 1200


def gen_password(length=10):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    text = re.sub(r"<[^>]+>", "", raw_html)
    return unescape(text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👑 MuDaSiR VIP Temp Mail Bot 👑\n\n"
        "Yo hi mausam ki ada dekh kar yaad aaya,\n"
        "Faqat kaise badaltay hain log jaan-e-jana.\n"
        "— Ahmad Faraz 🖤\n\n"
        "Commands:\n"
        "/create – Create email\n"
        "/inbox – Open inbox\n"
        "/domains – Select domain\n"
        "/custom – Custom email\n"
        "/help – Help menu"
    )

    keyboard = [
        [
            InlineKeyboardButton("✨ Create Email", callback_data="create"),
            InlineKeyboardButton("🌐 Domains", callback_data="domains"),
        ],
        [
            InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
            InlineKeyboardButton("✍️ Custom Email", callback_data="custom"),
        ],
    ]

    await update.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 HELP MENU\n\n"
        "Developer: MuDaSiR\n"
        "Powered by Mail.tm\n\n"
        "Use:\n"
        "/start – Start bot\n"
        "/create – Auto email\n"
        "/custom – Custom email\n"
        "/domains – Change domain\n"
        "/inbox – Inbox\n"
    )
    await update.message.reply_text(text)


async def show_domains(message, context):
    domains = []
    for page in range(1, 4):
        res = await asyncio.to_thread(
            requests.get, f"{BASE_URL}/domains?page={page}"
        )
        data = res.json().get("hydra:member", [])
        if not data:
            break
        domains.extend(data)

    if not domains:
        await message.reply_text("No domains available")
        return

    buttons = [
        [InlineKeyboardButton(d["domain"], callback_data=f"dom:{d['domain']}")]
        for d in domains[:12]
    ]
    await message.reply_text(
        "🌐 Select domain:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def create_account(name=None, domain=None):
    if not domain:
        res = await asyncio.to_thread(requests.get, f"{BASE_URL}/domains")
        domain = res.json()["hydra:member"][0]["domain"]

    username = name or f"user{random.randint(1000,9999)}"
    email = f"{username}@{domain}"
    password = gen_password()

    acc = await asyncio.to_thread(
        requests.post,
        f"{BASE_URL}/accounts",
        json={"address": email, "password": password},
    )
    if acc.status_code not in (200, 201):
        return None

    tok = await asyncio.to_thread(
        requests.post,
        f"{BASE_URL}/token",
        json={"address": email, "password": password},
    )

    return {"email": email, "token": tok.json().get("token")}


async def show_inbox(message, context):
    token = context.user_data.get("token")
    if not token:
        await message.reply_text("⚠️ Pehle /create karo")
        return

    headers = {"Authorization": f"Bearer {token}"}
    res = await asyncio.to_thread(
        requests.get, f"{BASE_URL}/messages", headers=headers
    )
    msgs = res.json().get("hydra:member", [])

    if not msgs:
        await message.reply_text("📭 Inbox empty")
        return

    buttons = []
    for m in msgs:
        subject = m.get("subject") or "(No Subject)"
        buttons.append(
            [InlineKeyboardButton(subject, callback_data=f"msg:{m['id']}")]
        )

    await message.reply_text(
        "📥 Inbox:", reply_markup=InlineKeyboardMarkup(buttons)
    )


async def read_message(query, context, msg_id):
    token = context.user_data.get("token")
    headers = {"Authorization": f"Bearer {token}"}

    res = await asyncio.to_thread(
        requests.get, f"{BASE_URL}/messages/{msg_id}", headers=headers
    )
    data = res.json()

    sender = data.get("from", {}).get("address", "Unknown")
    subject = data.get("subject") or "(No Subject)"

    body = ""
    if data.get("text"):
        body = data["text"]
    elif data.get("html"):
        body = clean_html(data["html"][0])

    if not body.strip():
        body = "No readable content"

    if len(body) > MAX_LEN:
        body = body[:MAX_LEN] + "\n--- trimmed ---"

    text = (
        f"FROM: {sender}\n"
        f"SUBJECT: {subject}\n"
        f"{'-'*30}\n"
        f"{body}"
    )

    keyboard = []
    if data.get("hasAttachments"):
        for a in data.get("attachments", []):
            keyboard.append(
                [
                    InlineKeyboardButton(
                        a.get("filename", "Attachment"),
                        url=f"{BASE_URL}{a['downloadUrl']}",
                    )
                ]
            )

    await query.message.reply_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "create":
        data = await create_account(domain=context.user_data.get("domain"))
        if not data:
            await q.message.reply_text("Failed to create email")
            return
        context.user_data.update(data)
        await q.message.reply_text(f"✅ Email created:\n{data['email']}")

    elif q.data == "domains":
        await show_domains(q.message, context)

    elif q.data.startswith("dom:"):
        context.user_data["domain"] = q.data.split(":", 1)[1]
        await q.message.reply_text(
            f"Domain set: {context.user_data['domain']}"
        )

    elif q.data == "custom":
        context.user_data["await_custom"] = True
        await q.message.reply_text("Custom name bhejo")

    elif q.data == "inbox":
        await show_inbox(q.message, context)

    elif q.data.startswith("msg:"):
        await read_message(q, context, q.data.split(":", 1)[1])


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("await_custom"):
        context.user_data["await_custom"] = False
        data = await create_account(
            name=update.message.text.strip(),
            domain=context.user_data.get("domain"),
        )
        if not data:
            await update.message.reply_text("Failed")
            return
        context.user_data.update(data)
        await update.message.reply_text(
            f"✅ Email created:\n{data['email']}"
        )


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("create", start))
app.add_handler(CommandHandler("inbox", lambda u, c: asyncio.create_task(show_inbox(u.message, c))))
app.add_handler(CommandHandler("domains", lambda u, c: asyncio.create_task(show_domains(u.message, c))))
app.add_handler(CommandHandler("custom", lambda u, c: asyncio.create_task(u.message.reply_text("Custom name bhejo"))))

app.add_handler(CallbackQueryHandler(menu))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling(drop_pending_updates=True)
