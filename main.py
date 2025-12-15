import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("TEMPMAIL_API_KEY")
BASE_URL = "https://api.temp-mail.io/api"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Temp Mail Bot Ready 🚀\n\n"
        "/domains - Available domains\n"
        "/create - Create email\n"
        "/inbox - Check inbox\n"
        "/delete - Delete email"
    )

async def domains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = requests.get(f"{BASE_URL}/domains", headers=HEADERS)
    data = r.json()
    msg = "Available Domains:\n" + "\n".join(data)
    await update.message.reply_text(msg)

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = requests.get(f"{BASE_URL}/domains", headers=HEADERS)
    domain = r.json()[0]

    payload = {"domain": domain}
    r = requests.post(f"{BASE_URL}/emails", json=payload, headers=HEADERS)
    data = r.json()

    context.user_data['email_id'] = data['id']
    context.user_data['email'] = data['address']

    await update.message.reply_text(f"Email Created:\n{data['address']}")

async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_id = context.user_data.get('email_id')
    if not email_id:
        await update.message.reply_text("Create email first")
        return

    r = requests.get(f"{BASE_URL}/emails/{email_id}", headers=HEADERS)
    mails = r.json().get('messages', [])

    if not mails:
        await update.message.reply_text("Inbox empty")
        return

    msg = "Inbox:\n"
    for m in mails:
        msg += f"From: {m['from']}\nSubject: {m['subject']}\n\n"

    await update.message.reply_text(msg)

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email_id = context.user_data.get('email_id')
    if not email_id:
        await update.message.reply_text("No email to delete")
        return

    requests.delete(f"{BASE_URL}/emails/{email_id}", headers=HEADERS)
    context.user_data.clear()

    await update.message.reply_text("Email deleted ✅")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("domains", domains))
app.add_handler(CommandHandler("create", create))
app.add_handler(CommandHandler("inbox", inbox))
app.add_handler(CommandHandler("delete", delete))

app.run_polling()
