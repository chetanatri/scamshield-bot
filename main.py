import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, ChatMemberHandler
)

TOKEN = os.getenv("BOT_TOKEN")  # 🔑 token from environment

# Database
conn = sqlite3.connect("scam.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER,
    username TEXT,
    scam_type TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reporter_id, username)
)
""")
conn.commit()

USERNAME, SCAM_TYPE = range(2)

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🔍 Check User"],
        ["🚨 Report Scammer"],
        ["ℹ️ How it Works"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Welcome to ScamShield Bot\n\n"
        "🔍 Check users\n🚨 Report scammers\n\nChoose below 👇",
        reply_markup=reply_markup
    )

# Check logic
async def check_username(update: Update, context: ContextTypes.DEFAULT_TYPE, username):
    cursor.execute("SELECT COUNT(*) FROM reports WHERE username=?", (username,))
    count = cursor.fetchone()[0]

    if count == 0:
        msg = f"✅ {username} has no reports."
    elif count <= 2:
        msg = f"⚠️ {username} has {count} reports (Low Risk)"
    elif count <= 5:
        msg = f"⚠️ {username} has {count} reports (Medium Risk)"
    else:
        msg = f"🚨 {username} has {count} reports (HIGH RISK)"

    await update.message.reply_text(msg)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check @username")
        return
    await check_username(update, context, context.args[0])

# Report flow
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter username (e.g., @abc123):")
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text

    if not username.startswith("@"):
        await update.message.reply_text("❌ Enter valid @username")
        return USERNAME

    context.user_data["username"] = username

    keyboard = [["Job Scam", "Investment Scam"], ["Other"]]
    await update.message.reply_text(
        "Select type:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return SCAM_TYPE

async def get_scam_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data["username"]
    scam_type = update.message.text
    reporter_id = update.effective_user.id

    try:
        cursor.execute(
            "INSERT INTO reports (reporter_id, username, scam_type) VALUES (?, ?, ?)",
            (reporter_id, username, scam_type)
        )
        conn.commit()
        msg = "✅ Report submitted"
    except:
        msg = "⚠️ You already reported this user"

    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Menu
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔍 Check User":
        await update.message.reply_text("Send @username")

    elif text == "🚨 Report Scammer":
        return await report(update, context)

    elif text.startswith("@"):
        await check_username(update, context, text)

# Group warning
async def welcome_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_member.new_chat_member.user

    if user.is_bot or not user.username:
        return

    username = f"@{user.username}"
    cursor.execute("SELECT COUNT(*) FROM reports WHERE username=?", (username,))
    count = cursor.fetchone()[0]

    if count > 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ {username} reported {count} times"
        )

# App
app = ApplicationBuilder().token(TOKEN).build()

conv = ConversationHandler(
    entry_points=[CommandHandler("report", report)],
    states={
        USERNAME: [MessageHandler(filters.TEXT, get_username)],
        SCAM_TYPE: [MessageHandler(filters.TEXT, get_scam_type)],
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check))
app.add_handler(conv)
app.add_handler(MessageHandler(filters.TEXT, handle_menu))
app.add_handler(ChatMemberHandler(welcome_check, ChatMemberHandler.CHAT_MEMBER))

# 🚀 Webhook setup for Railway
PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if WEBHOOK_URL:
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )
else:
    app.run_polling()
