import logging
import os
import openpyxl
import sqlite3
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# --- Loglarni sozlash ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Holatlarni aniqlash ---
CHOOSING_TEST, ANSWERING = range(2)

# --- Fayl yo'llari ---
EXCEL_FILE_PATH = "test_savollar.xlsx"
DB_NAME = "bot_data.db"

# --- Global o'zgaruvchilar ---
tests_data = []

# --- Ma'lumotlar bazasi funksiyalari ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            current_question_index INTEGER,
            score INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_user_data_from_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT current_question_index, score FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"current_question_index": result[0], "score": result[1]}
    return None

def save_user_data_to_db(user_id, current_question_index, score):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, current_question_index, score)
        VALUES (?, ?, ?)
    ''', (user_id, current_question_index, score))
    conn.commit()
    conn.close()

def delete_user_data_from_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- Exceldan savollarni yuklash ---
def load_tests_from_excel(file_path):
    global tests_data
    tests_data = []

    if not os.path.exists(file_path):
        logger.error(f"Excel fayli topilmadi: {file_path}")
        return

    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active

        for row_index in range(2, sheet.max_row + 1):
            question = sheet.cell(row=row_index, column=1).value
            option_a = sheet.cell(row=row_index, column=2).value
            option_b = sheet.cell(row=row_index, column=3).value
            option_c = sheet.cell(row=row_index, column=4).value
            option_d = sheet.cell(row=row_index, column=5).value
            correct_answer = sheet.cell(row=row_index, column=6).value

            if question:
                options = [opt for opt in [option_a, option_b, option_c, option_d] if opt is not None]
                tests_data.append({
                    "savol": str(question).strip(),
                    "variantlar": [str(o).strip() for o in options],
                    "togri_javob": str(correct_answer).strip()
                })
        logger.info(f"{len(tests_data)} ta savol yuklandi.")
    except Exception as e:
        logger.error(f"Excel yuklash xatosi: {e}")
        tests_data = []

# --- Bot funksiyalari ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_html(
        f"Salom, {user.mention_html()}! Testni boshlash uchun /test buyrug'ini bosing."
    )
    return CHOOSING_TEST

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not tests_data:
        await update.message.reply_text("Test savollari yuklanmagan.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    delete_user_data_from_db(user_id)
    save_user_data_to_db(user_id, 0, 0)

    await update.message.reply_text("Test boshlandi!")
    return await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_info = get_user_data_from_db(user_id)

    if not user_info:
        await update.message.reply_text("Xato: Test holati topilmadi. /test buyrug'ini qayta bosing.")
        return ConversationHandler.END

    current_index = user_info["current_question_index"]

    if current_index < len(tests_data):
        question_data = tests_data[current_index]
        question_text = f"Savol {current_index + 1}: {question_data['savol']}"

        keyboard = [
            [InlineKeyboardButton(option, callback_data=option)]
            for option in question_data['variantlar']
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.message.reply_text(question_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(question_text, reply_markup=reply_markup)

        return ANSWERING
    else:
        final_score = user_info["score"]
        total_questions = len(tests_data)
        msg = f"Test tugadi! Siz {final_score} / {total_questions} ball to'pladingiz."

        if update.callback_query:
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)

        delete_user_data_from_db(user_id)
        return ConversationHandler.END

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_answer = query.data
    user_info = get_user_data_from_db(user_id)

    if not user_info:
        await query.edit_message_text("Xato: Test holati topilmadi. /test buyrug'ini qayta bosing.")
        return ConversationHandler.END

    current_index = user_info["current_question_index"]
    score = user_info["score"]

    if current_index >= len(tests_data):
        await query.edit_message_text("Test allaqachon tugagan.")
        delete_user_data_from_db(user_id)
        return ConversationHandler.END

    question_data = tests_data[current_index]
    correct_answer = question_data["togri_javob"]

    if user_answer == correct_answer:
        score += 1
        feedback = "✅ To'g'ri javob!"
    else:
        feedback = f"❌ Noto'g'ri. To'g'ri javob: {correct_answer}"

    try:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.edit_message_text(f"{query.message.text}\n\n{feedback}")
    except Exception as e:
        logger.error(f"Xabarni yangilashda xato: {e}")
        await query.message.reply_text(feedback)

    current_index += 1
    save_user_data_to_db(user_id, current_index, score)
    await asyncio.sleep(0.7)

    return await ask_question(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    delete_user_data_from_db(user_id)
    await update.message.reply_text("Test bekor qilindi. /start orqali qaytadan boshlang.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning('Xato: "%s" - "%s"', update, context.error)

# --- Botni ishga tushirish ---
def main():
    TOKEN = os.environ.get("BOT_TOKEN") or "7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg"
    if not TOKEN or "7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg" in TOKEN:
        logger.error("Iltimos, BOT_TOKEN ni to‘g‘ri kiriting.")
        return

    init_db()
    load_tests_from_excel(EXCEL_FILE_PATH)

    application = Application.builder().token(7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("test", start_test)],
        states={
            CHOOSING_TEST: [CommandHandler("test", start_test)],
            ANSWERING: [CallbackQueryHandler(handle_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    application.add_error_handler(error_handler)

    logger.info("Bot ishga tushirildi...")
    application.run_polling()

if __name__ == "__main__":
    main()
