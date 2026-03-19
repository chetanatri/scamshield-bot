import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, ChatMemberHandler
)

# 🔑 Token
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing!")

# 🗄️ Database
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

# 🚀 Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🔍 Check User"],
        ["🚨 Report Scammer"],
        ["ℹ️ How it Works"]
    ]
    await update.message.reply_text(
        "👋 Welcome to ScamShield Bot\n\nChoose option 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# 🔍 Check
async def check_username(update: Update, context: ContextTypes.DEFAULT_TYPE, username):
    cursor.execute("SELECT COUNT(*) FROM reports WHERE username=?", (username,))
    count = cursor.fetchone()[0]

    msg = f"{username} has {count} reports"
    await update.message.reply_text(msg)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        await check_username(update, context, context.args[0])

# 🚨 Report
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter username (@abc):")
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    context.user_data["username"] = username
    await update.message.reply_text("Type scam type:")
    return SCAM_TYPE

async def get_scam_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cursor.execute(
            "INSERT INTO reports (reporter_id, username, scam_type) VALUES (?, ?, ?)",
            (update.effective_user.id, context.user_data["username"], update.message.text)
        )
        conn.commit()
        await update.message.reply_text("Reported!")
    except:
        await update.message.reply_text("Already reported")
    return ConversationHandler.END

# 🏁 App
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
app.add_handler(conv_handler)

# ⬇️ KEEP THIS LAST
app.add_handler(MessageHandler(filters.TEXT, handle_menu))

print("✅ Bot started...")

# 🚨 IMPORTANT: Railway requires PORT binding
PORT = int(os.environ.get("PORT", 8080))

app.run_polling()
