import sqlite3
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, ChatMemberHandler
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN missing!")

# DB
conn = sqlite3.connect("scam.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER,
    contact TEXT,
    contact_type TEXT,
    scam_type TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(reporter_id, contact)
)
""")
conn.commit()

# States
TYPE, CONTACT, SCAM = range(3)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🔍 Check Contact"],
        ["🚨 Report Suspicious"],
        ["ℹ️ How it Works"]
    ]
    await update.message.reply_text(
        "👋 ScamShield Bot\n\n"
        "Check or report suspicious contacts (Telegram, Phone, Instagram)",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# CHECK
async def check_contact(update: Update, context: ContextTypes.DEFAULT_TYPE, contact):
    cursor.execute("SELECT COUNT(*), contact_type FROM reports WHERE contact=?", (contact,))
    result = cursor.fetchone()

    count = result[0] if result else 0
    ctype = result[1] if result and result[1] else "Unknown"

    if count == 0:
        msg = f"✅ No reports found for {contact}"
    elif count <= 2:
        msg = f"⚠️ {contact} has {count} reports (Low Risk)\nType: {ctype}"
    elif count <= 5:
        msg = f"⚠️ {contact} has {count} reports (Medium Risk)\nType: {ctype}"
    else:
        msg = f"🚨 {contact} has {count} reports (HIGH RISK)\nType: {ctype}"

    await update.message.reply_text(msg)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        await check_contact(update, context, context.args[0])

# REPORT FLOW
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["Telegram Username"], ["Phone Number"], ["Instagram ID"]]
    await update.message.reply_text(
        "Select contact type:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return TYPE

async def get_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["type"] = update.message.text
    await update.message.reply_text("Enter contact (e.g., @user or number):")
    return CONTACT

async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text
    keyboard = [["Job Scam", "Investment Scam"], ["Other"]]
    await update.message.reply_text(
        "Select scam type:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return SCAM

async def save_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cursor.execute(
            "INSERT INTO reports (reporter_id, contact, contact_type, scam_type) VALUES (?, ?, ?, ?)",
            (
                update.effective_user.id,
                context.user_data["contact"],
                context.user_data["type"],
                update.message.text
            )
        )
        conn.commit()
        await update.message.reply_text("✅ Report submitted", reply_markup=ReplyKeyboardRemove())
    except:
        await update.message.reply_text("⚠️ Already reported", reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

# MENU
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔍 Check Contact":
        await update.message.reply_text("Send contact like:\n@username OR phone number")

    elif text == "🚨 Report Suspicious":
        return await report(update, context)

    elif text == "ℹ️ How it Works":
        await update.message.reply_text(
            "Users report suspicious contacts.\n"
            "More reports = higher risk.\n"
            "Always verify before sending money."
        )

    else:
        await check_contact(update, context, text)

# GROUP WARNING
async def welcome_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_member.new_chat_member.user

    if user.is_bot or not user.username:
        return

    username = f"@{user.username}"
    cursor.execute("SELECT COUNT(*) FROM reports WHERE contact=?", (username,))
    count = cursor.fetchone()[0]

    if count > 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ {username} reported {count} times"
        )

# APP
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("report", report),
        MessageHandler(filters.Regex("^🚨 Report Suspicious$"), report)
    ],
    states={
        TYPE: [MessageHandler(filters.TEXT, get_type)],
        CONTACT: [MessageHandler(filters.TEXT, get_contact)],
        SCAM: [MessageHandler(filters.TEXT, save_report)],
    },
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("check", check))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT, handle_menu))
app.add_handler(ChatMemberHandler(welcome_check, ChatMemberHandler.CHAT_MEMBER))

print("✅ Bot running...")

app.run_polling()
