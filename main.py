import os, re, random, string, requests
from html import unescape
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = "https://api.mail.tm"

# ---------------- UTILS ----------------

def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "img", "noscript"]):
        t.decompose()
    text = unescape(soup.get_text("\n"))
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)

def extract_otp(text):
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group(0) if m else None

def domains():
    r = requests.get(f"{BASE}/domains", timeout=15)
    return [d["domain"] for d in r.json()["hydra:member"]]

def create_account(email, password):
    requests.post(f"{BASE}/accounts", json={"address": email, "password": password}, timeout=15)

def get_token(email, password):
    r = requests.post(f"{BASE}/token", json={"address": email, "password": password}, timeout=15)
    return r.json()["token"]

def messages(token):
    r = requests.get(f"{BASE}/messages", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    return r.json().get("hydra:member", [])

def message(token, mid):
    r = requests.get(f"{BASE}/messages/{mid}", headers={"Authorization": f"Bearer {token}"}, timeout=15)
    return r.json()

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[
        InlineKeyboardButton("📧 Create Email", callback_data="create"),
        InlineKeyboardButton("📥 Inbox", callback_data="inbox")
    ]]
    await update.message.reply_text(
        "🩷 **MuDaSiR VIP Temp Mail**\n\nClean • Readable • OTP-Smart",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ---------------- CREATE ----------------

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    name = "Mudasir"
    user = name.lower() + "".join(random.choices(string.digits, k=6))
    password = f"{name}786$"
    domain = random.choice(domains())
    email = f"{user}@{domain}"

    create_account(email, password)
    token = get_token(email, password)

    context.user_data.clear()
    context.user_data["token"] = token

    await q.message.reply_text(
        f"📧 **EMAIL CREATED**\n\n`{email}`\n\nPassword:\n`{password}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Inbox", callback_data="inbox")]
        ])
    )

# ---------------- INBOX ----------------

async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    token = context.user_data.get("token")
    if not token:
        await q.message.reply_text("❌ Create email first")
        return

    mails = messages(token)
    if not mails:
        await q.message.reply_text("📭 Inbox empty")
        return

    kb = [[InlineKeyboardButton(m.get("subject","No Subject")[:40], callback_data=f"read:{m['id']}")] for m in mails]
    await q.message.reply_text("📥 **Inbox**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

# ---------------- READ ----------------

async def read(update: Update, context: ContextTypes.DEFAULT_TYPE, mid):
    q = update.callback_query
    token = context.user_data["token"]

    m = message(token, mid)
    body = clean_html("\n".join(m.get("html", [])) or m.get("text",""))
    otp = extract_otp(body)

    text = ""
    buttons = []

    if otp:
        text += f"🔐 **OTP CODE**\n\n`{otp}`\n\n"
        buttons.append(InlineKeyboardButton("📋 Copy Code", callback_data=f"copy:{otp}"))

    text += f"📩 **From:** {m['from']['address']}\n📌 **Subject:** {m.get('subject','')}"
    buttons.append(InlineKeyboardButton("🌐 View Full Email", callback_data=f"full:{mid}"))

    await q.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([buttons])
    )

# ---------------- COPY / FULL ----------------

async def copy_code(update: Update, context: ContextTypes.DEFAULT_TYPE, code):
    await update.callback_query.message.reply_text(f"`{code}`", parse_mode="Markdown")

async def full_mail(update: Update, context: ContextTypes.DEFAULT_TYPE, mid):
    q = update.callback_query
    token = context.user_data["token"]
    m = message(token, mid)
    body = clean_html("\n".join(m.get("html", [])) or m.get("text",""))
    await q.message.reply_text(f"```{body[:3800]}```", parse_mode="Markdown")

# ---------------- ROUTER ----------------

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data
    if d == "create": await create(update, context)
    elif d == "inbox": await inbox(update, context)
    elif d.startswith("read:"): await read(update, context, d.split(":")[1])
    elif d.startswith("copy:"): await copy_code(update, context, d.split(":")[1])
    elif d.startswith("full:"): await full_mail(update, context, d.split(":")[1])

# ---------------- MAIN ----------------

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(router))
app.run_polling()
