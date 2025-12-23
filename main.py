import os, re, random, string, requests
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

def get_domains():
    r = requests.get(f"{BASE}/domains", timeout=15)
    return [d["domain"] for d in r.json()["hydra:member"]]

def create_account(email, password):
    requests.post(
        f"{BASE}/accounts",
        json={"address": email, "password": password},
        timeout=15,
    )

def get_token(email, password):
    r = requests.post(
        f"{BASE}/token",
        json={"address": email, "password": password},
        timeout=15,
    )
    return r.json()["token"]

def get_messages(token):
    r = requests.get(
        f"{BASE}/messages",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return r.json().get("hydra:member", [])

def get_message(token, mid):
    r = requests.get(
        f"{BASE}/messages/{mid}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return r.json()

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poetry = (
        "❝\n"
        "یہ مجھے چین کیوں نہیں پڑتا\n"
        "ایک ہی شخص تھا جہاں میں کیا\n\n"
        "ہم نے مانا کہ تغافل نہ کرو گے، لیکن\n"
        "خاک ہو جائیں گے ہم، تم کو خبر ہونے تک\n"
        "❞"
    )

    text = (
        "🩷 **MuDaSiR VIP Temp Mail Bot**\n\n"
        "Assalamualaikum "
        f"**{update.effective_user.first_name}** ✨\n\n"
        f"{poetry}\n\n"
        "📧 Temporary Email • 🔐 OTP Smart • 📩 Clean Inbox\n"
        "👨‍💻 Developer: **MuDaSiR**"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📧 Create Mail", callback_data="create"),
            InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="help"),
            InlineKeyboardButton("👨‍💻 Dev", callback_data="dev"),
        ]
    ])

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# ---------------- HELP ----------------

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🩷 **MuDaSiR VIP Temp Mail — Help**\n\n"
        "🛠 **How to Use:**\n\n"
        "1️⃣ Create Mail\n"
        "• Bot auto generates Email, Username & Password\n\n"
        "2️⃣ Inbox\n"
        "• Receive emails instantly\n\n"
        "3️⃣ OTP Mail\n"
        "• OTP shown separately for easy copy\n\n"
        "4️⃣ View Full Email\n"
        "• Clean & readable format\n\n"
        "ℹ️ **Note:**\n"
        "Telegram clipboard direct access allow nahi karta.\n"
        "Code ko **long-press → copy** karein.\n\n"
        "👨‍💻 Developer: **MuDaSiR**"
    )
    await update.callback_query.message.reply_text(text, parse_mode="Markdown")

# ---------------- CREATE ----------------

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query

    pak_names = ["Ayesha", "Hira", "Zainab", "Fatima", "Iqra"]
    name = random.choice(pak_names)
    digits = "".join(random.choices(string.digits, k=6))
    username = f"{name.lower()}{digits}"
    password = f"{name}786$"

    domain = random.choice(get_domains())
    email = f"{username}@{domain}"

    create_account(email, password)
    token = get_token(email, password)

    context.user_data.clear()
    context.user_data["token"] = token

    text = (
        "🩷 **EMAIL CREATED**\n\n"
        f"📧 **Email:**\n`{email}`\n\n"
        f"📛 **Name:**\n`{name}`\n\n"
        f"🔇 **Username:**\n`{username}`\n\n"
        f"💻 **Password:**\n`{password}`"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 Copy Email", callback_data=f"copy:{email}"),
            InlineKeyboardButton("📋 Copy User", callback_data=f"copy:{username}"),
        ],
        [
            InlineKeyboardButton("📋 Copy Pass", callback_data=f"copy:{password}"),
            InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
        ]
    ])

    await q.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# ---------------- INBOX ----------------

async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    token = context.user_data.get("token")

    if not token:
        await q.message.reply_text("❌ Pehle email create karein.")
        return

    mails = get_messages(token)
    if not mails:
        await q.message.reply_text("📭 Inbox empty hai.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(m.get("subject", "No Subject")[:40], callback_data=f"read:{m['id']}")]
        for m in mails
    ])

    await q.message.reply_text(
        "📥 **Inbox**",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# ---------------- READ ----------------

async def read(update: Update, context: ContextTypes.DEFAULT_TYPE, mid):
    q = update.callback_query
    token = context.user_data["token"]

    m = get_message(token, mid)
    body = clean_html("\n".join(m.get("html", [])) or m.get("text", ""))
    otp = extract_otp(body)

    text = ""
    buttons = []

    if otp:
        text += f"🔐 **OTP CODE**\n\n`{otp}`\n\n"
        buttons.append(InlineKeyboardButton("📋 Copy Code", callback_data=f"copy:{otp}"))

    text += (
        f"📩 **From:** {m['from']['address']}\n"
        f"📌 **Subject:** {m.get('subject','')}"
    )

    buttons.append(InlineKeyboardButton("🌐 View Full Email", callback_data=f"full:{mid}"))

    await q.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([buttons]),
    )

# ---------------- COPY / FULL ----------------

async def copy_text(update: Update, context: ContextTypes.DEFAULT_TYPE, value):
    await update.callback_query.message.reply_text(f"`{value}`", parse_mode="Markdown")

async def full_mail(update: Update, context: ContextTypes.DEFAULT_TYPE, mid):
    q = update.callback_query
    token = context.user_data["token"]
    m = get_message(token, mid)
    body = clean_html("\n".join(m.get("html", [])) or m.get("text", ""))
    await q.message.reply_text(f"```{body[:3800]}```", parse_mode="Markdown")

# ---------------- ROUTER ----------------

async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data

    if d == "create":
        await create(update, context)
    elif d == "inbox":
        await inbox(update, context)
    elif d == "help":
        await help_cmd(update, context)
    elif d.startswith("read:"):
        await read(update, context, d.split(":")[1])
    elif d.startswith("copy:"):
        await copy_text(update, context, d.split(":", 1)[1])
    elif d.startswith("full:"):
        await full_mail(update, context, d.split(":")[1])

# ---------------- MAIN ----------------

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(router))
app.run_polling()
