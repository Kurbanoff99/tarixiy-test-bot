
import logging
import os
import sqlite3
import openpyxl
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = "@Tarix_dtmadmin"
ADMINS = [int(i) for i in os.getenv("ADMINS", "123456789").split(",")]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    premium_access BOOLEAN DEFAULT 0
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    question TEXT,
    a TEXT,
    b TEXT,
    c TEXT,
    d TEXT,
    correct TEXT,
    is_premium BOOLEAN DEFAULT 0
)''')
conn.commit()

def load_tests_from_excel(file_path, is_premium=False):
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not row or row[0] is None:
            continue
        question, a, b, c, d, correct = row
        cursor.execute(
            'INSERT INTO tests (filename, question, a, b, c, d, correct, is_premium) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (os.path.basename(file_path), question, a, b, c, d, str(correct).lower(), int(is_premium))
        )
    conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                   (user.id, user.username, user.full_name))
    conn.commit()
    await update.message.reply_text("Assalomu alaykum! Excel test faylini yuboring yoki /tests buyrug‘idan foydalaning.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.document
    if not file.file_name.endswith(".xlsx"):
        await update.message.reply_text("❗ Faqat .xlsx formatdagi fayl yuboring.")
        return
    file_path = f"./downloads/{file.file_name}"
    os.makedirs("./downloads", exist_ok=True)
    await file.get_file().download_to_drive(file_path)
    is_premium = "premium" in file.file_name.lower()
    load_tests_from_excel(file_path, is_premium=is_premium)
    await update.message.reply_text("✅ Testlar bazaga muvaffaqiyatli yuklandi.")

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"💳 Premium testlar uchun {ADMIN_USERNAME} bilan bog‘laning."
    )
    for admin in ADMINS:
        await context.bot.send_message(admin, f"📩 @{user.username} premium so‘ramoqda.")

async def activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("Foydalanuvchi ID kiriting: /activate 123456789")
        return
    uid = int(context.args[0])
    cursor.execute("UPDATE users SET premium_access = 1 WHERE user_id = ?", (uid,))
    conn.commit()
    await update.message.reply_text(f"✅ {uid} premiumga qo‘shildi.")

async def deactivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("Foydalanuvchi ID kiriting: /deactivate 123456789")
        return
    uid = int(context.args[0])
    cursor.execute("UPDATE users SET premium_access = 0 WHERE user_id = ?", (uid,))
    conn.commit()
    await update.message.reply_text(f"❌ {uid} premiumdan chiqarildi.")

async def tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT premium_access FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    premium = row[0] if row else 0
    cursor.execute("SELECT DISTINCT filename, is_premium FROM tests")
    files = cursor.fetchall()
    buttons = []
    for f, is_premium in files:
        if is_premium and not premium:
            continue
        buttons.append([InlineKeyboardButton(f"{'🔒' if is_premium else ''}{f}", callback_data=f"test:{f}")])
    if not premium:
        buttons.append([InlineKeyboardButton("🔓 Premium testlar haqida", callback_data="premium_info")])
    await update.message.reply_text("Quyidagilardan tanlang:", reply_markup=InlineKeyboardMarkup(buttons))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "premium_info":
        await premium(update, context)
        return
    if data.startswith("test:"):
        filename = data[5:]
        cursor.execute("SELECT question, a, b, c, d FROM tests WHERE filename = ?", (filename,))
        tests = cursor.fetchall()
        for q, a, b, c, d in tests:
            text = f"{q}\nA) {a}\nB) {b}\nC) {c}\nD) {d}"
            await query.message.reply_text(text)

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    for admin in ADMINS:
        await context.bot.send_message(admin, f"📩 @{user.username} yubordi: {update.message.text}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("premium", premium))
    app.add_handler(CommandHandler("activate", activate))
    app.add_handler(CommandHandler("deactivate", deactivate))
    app.add_handler(CommandHandler("tests", tests))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    app.run_polling()

if __name__ == "__main__":
    main()
