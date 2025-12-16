MuDaSiR VIP Mail.tm Telegram Bot (FINAL – STABLE)

✔ Inbox works

✔ No false 'Create email first'

✔ Domains selectable

✔ Custom email works

✔ Clean async-safe logic

import os import random import string import asyncio import requests from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, )

BOT_TOKEN = os.getenv("BOT_TOKEN") BASE_URL = "https://api.mail.tm"

================= UTIL =================

def gen_password(length=12): return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): text = ( "👑 MuDaSiR VIP Temp Mail Bot 👑\n" "━━━━━━━━━━━━━━━━━━━━━━\n\n" "> 🌙 Yo hi mausam ki ada dekh kar yaad aaya\n" "> Faqat kaise badaltay hain log, jaan-e-jana\n>\n" "> Tum bhi shayad isi mausam mein kahin kho gaye thay\n" "> Hum ne har simt tumhein dhoondha, magar paaya na gaya\n>\n" "> — Ahmad Faraz ✨\n\n" "📧 Create • 📥 Inbox • 🌐 Domains" )

keyboard = [
    [InlineKeyboardButton("✨ Create", callback_data="create"), InlineKeyboardButton("🌐 Domains", callback_data="domains")],
    [InlineKeyboardButton("📥 Inbox", callback_data="inbox"), InlineKeyboardButton("✍️ Custom", callback_data="custom")],
]

await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

================= DOMAINS =================

async def show_domains(message, context): domains = [] for page in range(1, 4): res = await asyncio.to_thread(requests.get, f"{BASE_URL}/domains?page={page}") data = res.json().get("hydra:member", []) if not data: break domains.extend(data)

if not domains:
    await message.reply_text("❌ No domains available")
    return

buttons = []
for d in domains[:10]:
    buttons.append([InlineKeyboardButton(d['domain'], callback_data=f"dom:{d['domain']}")])

await message.reply_text("🌐 *Select Domain*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

================= CREATE ACCOUNT =================

async def create_account(name=None, domain=None): if not domain: res = await asyncio.to_thread(requests.get, f"{BASE_URL}/domains") domain = res.json()["hydra:member"][0]["domain"]

username = name or f"mudasir{random.randint(1000,9999)}"
email = f"{username}@{domain}"
password = gen_password()

acc = await asyncio.to_thread(
    requests.post,
    f"{BASE_URL}/accounts",
    json={"address": email, "password": password}
)
if acc.status_code not in (200, 201):
    return None

tok = await asyncio.to_thread(
    requests.post,
    f"{BASE_URL}/token",
    json={"address": email, "password": password}
)
token = tok.json().get("token")

return {"email": email, "token": token}

================= INBOX =================

async def show_inbox(message, context): token = context.user_data.get("token") if not token: await message.reply_text("❌ Create email first") return

headers = {"Authorization": f"Bearer {token}"}
res = await asyncio.to_thread(requests.get, f"{BASE_URL}/messages", headers=headers)
msgs = res.json().get("hydra:member", [])

if not msgs:
    await message.reply_text("📭 Inbox empty", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="refresh")]]))
    return

buttons = [[InlineKeyboardButton(f"📩 {m.get('subject') or '(No subject)'}", callback_data=f"msg:{m['id']}")] for m in msgs]
buttons.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh")])

await message.reply_text("📥 *Inbox*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

================= READ MESSAGE =================

async def read_message(query, context, msg_id): token = context.user_data.get("token") headers = {"Authorization": f"Bearer {token}"} m = await asyncio.to_thread(requests.get, f"{BASE_URL}/messages/{msg_id}", headers=headers) data = m.json()

sender = data.get("from", {}).get("address", "")
subject = data.get("subject", "")
body = data.get("text") or (data.get("html", [""])[0])

text = (
    f"📧 *From:* **{sender}**\n"
    f"📝 *Subject:* **{subject}**\n\n"
    f"> {body[:3500]}"
)

kb = []
if data.get("hasAttachments"):
    for a in data.get("attachments", []):
        kb.append([InlineKeyboardButton(f"📎 {a['filename']}", url=f"{BASE_URL}{a['downloadUrl']}")])

kb.append([InlineKeyboardButton("🔄 Refresh Inbox", callback_data="refresh")])

await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

================= MENU =================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE): q = update.callback_query await q.answer()

if q.data == "create":
    data = await create_account(domain=context.user_data.get("domain"))
    if not data:
        await q.message.reply_text("❌ Failed to create email")
        return
    context.user_data.update(data)
    await q.message.reply_text(f"✅ Email Created\n📧 `{data['email']}`", parse_mode="Markdown")

elif q.data == "domains":
    await show_domains(q.message, context)

elif q.data.startswith("dom:"):
    context.user_data["domain"] = q.data.split(":", 1)[1]
    await q.message.reply_text(f"✅ Domain selected: {context.user_data['domain']}")

elif q.data == "custom":
    context.user_data["await_custom"] = True
    await q.message.reply_text("✍️ Send custom email name")

elif q.data in ("inbox", "refresh"):
    await show_inbox(q.message, context)

elif q.data.startswith("msg:"):
    await read_message(q, context, q.data.split(":", 1)[1])

================= TEXT =================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): if context.user_data.get("await_custom"): context.user_data["await_custom"] = False data = await create_account(name=update.message.text.strip(), domain=context.user_data.get("domain")) if not data: await update.message.reply_text("❌ Failed to create email") return context.user_data.update(data) await update.message.reply_text(f"✅ Email Created\n📧 {data['email']}", parse_mode="Markdown")

================= RUN =================

app = ApplicationBuilder().token(BOT_TOKEN).build() app.add_handler(CommandHandler("start", start)) app.add_handler(CommandHandler("inbox", lambda u, c: show_inbox(u.message, c))) app.add_handler(CallbackQueryHandler(menu)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling(drop_pending_updates=True)
