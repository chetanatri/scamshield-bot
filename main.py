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
    raise ValueError("BOT_TOKEN is missing!")

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

# States
USERNAME, SCAM_TYPE = range(2)

# 🚀 Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🔍 Check User"],
        ["🚨 Report Scammer"],
        ["ℹ️ How it Works"]
    ]
    await update.message.reply_text(
        "👋 Welcome to ScamShield Bot\n\nChoose an option 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# 🔍 Check
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
    if context.args:
        await check_username(update, context, context.args[0])

# 🚨 Report flow
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter scammer username (e.g., @abc123):")
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text

    if not username.startswith("@"):
        await update.message.reply_text("❌ Enter valid @username")
        return USERNAME

    context.user_data["username"] = username

    keyboard = [["Job Scam", "Investment Scam"], ["Other"]]
    await update.message.reply_text(
        "Select scam type:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return SCAM_TYPE

async def get_scam_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cursor.execute(
            "INSERT INTO reports (reporter_id, username, scam_type) VALUES (?, ?, ?)",
            (update.effective_user.id, context.user_data["username"], update.message.text)
        )
        conn.commit()
        await update.message.reply_text("✅ Report submitted", reply_markup=ReplyKeyboardRemove())
    except:
        await update.message.reply_text("⚠️ You already reported this user", reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# 📱 Menu handler (FIXED)
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔍 Check User":
        await update.message.reply_text("Send username like:\n@testuser123")

    elif text == "🚨 Report Scammer":
        return await report(update, context)

    elif text == "ℹ️ How it Works":
        await update.message.reply_text(
            "📌 Users report suspicious accounts.\n"
            "Check usernames before dealing.\n"
            "⚠️ More reports = higher risk."
        )

    elif text.startswith("@"):
        await check_username(update, context, text)

# 🚨 Group warning
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
            text=f"⚠️ Warning: {username} reported {count} times"
        )

# 🏁 App setup
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("report", report),
        MessageHandler(filters.Regex("^🚨 Report Scammer$"), report)
    ],
    states={
        USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
        SCAM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_scam_type)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check))

# IMPORTANT ORDER
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT, handle_menu))
app.add_handler(ChatMemberHandler(welcome_check, ChatMemberHandler.CHAT_MEMBER))

print("✅ Bot running...")

app.run_polling()
