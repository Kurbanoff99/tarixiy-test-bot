import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
import openpyxl

BOT_TOKEN = "TOKENINGIZNI_KIRITING"
ADMINS = ["@Tarix_dtmadmin"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "tests.db"
os.makedirs("data", exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                savol TEXT,
                a TEXT,
                b TEXT,
                c TEXT,
                d TEXT,
                correct TEXT,
                is_premium INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Testlarni yuboring yoki /tests buyrug'ini bosing.")

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".xlsx"):
        return await update.message.reply_text("Faqat .xlsx fayllarni yuboring.")

    file = await document.get_file()
    file_path = f"data/{document.file_name}"
    await file.download_to_drive(file_path)

    is_premium = 1 if "premium" in document.file_name.lower() else 0
    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        for row in rows:
            if len(row) >= 6:
                c.execute('''
                    INSERT INTO tests (filename, savol, a, b, c, d, correct, is_premium)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (document.file_name, *row, is_premium))
        conn.commit()

    await update.message.reply_text(f"✅ {len(rows)} ta test yuklandi: {document.file_name}")

async def tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT filename FROM tests WHERE is_premium = 0")
        files = [r[0] for r in c.fetchall()]

    buttons = [[InlineKeyboardButton(file, callback_data=f"test_{file}")] for file in files]
    buttons.append([InlineKeyboardButton("🔓 Premium testlar haqida", callback_data="premium_info")])

    await update.message.reply_text("Quyidagilardan tanlang:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("test_"):
        filename = data[5:]
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT savol, a, b, c, d, correct FROM tests WHERE filename = ?", (filename,))
            tests = c.fetchall()

        text = ""
        for idx, (savol, a, b, c, d, correct) in enumerate(tests, start=1):
            text += f"{idx}. {savol}
A) {a}
B) {b}
C) {c}
D) {d}
To‘g‘ri javob: {correct.upper()}

"
        await query.message.reply_text(text if text else "Testlar topilmadi.")

    elif data == "premium_info":
        await query.message.reply_text("Premium testlar pullik. To‘lov uchun @Tarix_dtmadmin ga yozing.")

async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    for admin in ADMINS:
        await context.bot.send_message(chat_id=admin, text=f"❗ Noma'lum xabar: {user.username} - {update.message.text}")
    await update.message.reply_text("Iltimos, /tests yoki .xlsx fayl yuboring.")

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("tests", tests))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.Document.ALL, file_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    application.run_polling()

if __name__ == "__main__":
    main()