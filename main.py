import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, ChatMemberHandler
)

# 🔑 Token from Railway Variables
TOKEN = os.getenv("BOT_TOKEN")

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
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Welcome to ScamShield Bot\n\n"
        "🔍 Check if a user is reported\n"
        "🚨 Report a scammer\n\n"
        "⚠️ Always verify before sending money!\n\n"
        "Choose an option 👇",
        reply_markup=reply_markup
    )

# 🔍 Check logic
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

# Command check
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check @username")
        return
    await check_username(update, context, context.args[0])

# 🚨 Report start
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter scammer username (e.g., @abc123):")
    return USERNAME

# Get username
async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text

    if not username.startswith("@"):
        await update.message.reply_text("❌ Please enter a valid username starting with @")
        return USERNAME

    # Prevent self-report
    if update.effective_user.username and username.lower() == f"@{update.effective_user.username}".lower():
        await update.message.reply_text("❌ You cannot report yourself.")
        return ConversationHandler.END

    context.user_data["username"] = username

    keyboard = [["Job Scam", "Investment Scam"], ["Adult Scam", "Other"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text("Select scam type:", reply_markup=reply_markup)
    return SCAM_TYPE

# Save report (duplicate protected)
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

        await update.message.reply_text(
            "✅ Report submitted successfully.",
            reply_markup=ReplyKeyboardRemove()
        )

    except sqlite3.IntegrityError:
        await update.message.reply_text(
            "⚠️ You already reported this user.",
            reply_markup=ReplyKeyboardRemove()
        )

    return ConversationHandler.END

# ❌ Cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# 📱 Menu + auto check
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔍 Check User":
        await update.message.reply_text("Send username like:\n@testuser123")

    elif text == "🚨 Report Scammer":
        return await report(update, context)

    elif text == "ℹ️ How it Works":
        await update.message.reply_text(
            "📌 How it works:\n\n"
            "1. Users report suspicious accounts\n"
            "2. Reports are stored\n"
            "3. You can check usernames\n\n"
            "⚠️ More reports = higher risk"
        )

    elif text.startswith("@"):
        await check_username(update, context, text)

# 🚨 Group join warning
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
    entry_points=[CommandHandler("report", report)],
    states={
        USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
        SCAM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_scam_type)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
app.add_handler(ChatMemberHandler(welcome_check, ChatMemberHandler.CHAT_MEMBER))

print("✅ Bot is running...")

# 🚀 FINAL RUN (24/7 stable)
app.run_polling()
