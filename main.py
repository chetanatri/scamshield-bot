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
async def check_contact(update: Update, context: ContextTypes.DEFAULT)
