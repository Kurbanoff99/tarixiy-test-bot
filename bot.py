., [17.06.2025 0:55]
import logging
import os
import openpyxl
# import sqlite3
# import asyncio # Yangi import: Asinxron operatsiyalar uchun

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler, # <-- Mana bu import to'g'ri ekanligiga ishonch hosil qiling
)

# --- Loglarni sozlash ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(name)

# --- Holatlarni aniqlash ---
CHOOSING_TEST, ANSWERING = range(2)

# --- Fayl yo'llari ---
EXCEL_FILE_PATH = "test_savollar.xlsx"
DB_NAME = "bot_data.db"

# --- Global o'zgaruvchilar ---
tests_data = [] # Exceldan yuklangan savollar shu yerda saqlanadi

# --- Ma'lumotlar bazasi funksiyalari ---
def init_db():
    """Ma'lumotlar bazasini ishga tushiradi va kerakli jadvallarni yaratadi."""
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
    logger.info("Ma'lumotlar bazasi ishga tushirildi.")

def get_user_data_from_db(user_id):
    """Foydalanuvchi ma'lumotlarini ma'lumotlar bazasidan yuklaydi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT current_question_index, score FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {"current_question_index": result[0], "score": result[1]}
    return None

def save_user_data_to_db(user_id, current_question_index, score):
    """Foydalanuvchi ma'lumotlarini ma'lumotlar bazasiga saqlaydi yoki yangilaydi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, current_question_index, score)
        VALUES (?, ?, ?)
    ''', (user_id, current_question_index, score))
    conn.commit()
    conn.close()

def delete_user_data_from_db(user_id):
    """Foydalanuvchi ma'lumotlarini ma'lumotlar bazasidan o'chiradi."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    logger.info(f"Foydalanuvchi {user_id} ma'lumotlari DBdan o'chirildi.")

# --- Exceldan test savollarini yuklash funksiyasi ---
def load_tests_from_excel(file_path):
    """Excel faylidan test savollarini yuklaydi."""
    global tests_data
    tests_data = []

    if not os.path.exists(file_path):
        logger.error(f"Xato: '{file_path}' fayli topilmadi. Bot test savollarisiz ishlaydi.")
        return

    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active # Aktiv ishchi varaqni olish

        # Birinchi qator sarlavha deb hisoblaymiz, shuning uchun 2-qatordan boshlaymiz
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

., [17.06.2025 0:55]
"togri_javob": str(correct_answer).strip()
                })
        logger.info(f"Exceldan {len(tests_data)} ta savol muvaffaqiyatli yuklandi.")
    except Exception as e:
        logger.error(f"Excel faylini o'qishda xato yuz berdi: {e}")
        tests_data = []

# --- Bot handler funksiyalari ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bot /start buyrug'ini olganda salomlashish xabarini yuboradi."""
    user = update.effective_user
    await update.message.reply_html(
        f"Salom, {user.mention_html()}! Men test botiman. Testni boshlash uchun /test buyrug'ini bosing."
    )
    return CHOOSING_TEST

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Testni boshlaydi va birinchi savolni beradi."""
    if not tests_data:
        await update.message.reply_text("Test savollari yuklanmagan. Iltimos, administratorga murojaat qiling.")
        return ConversationHandler.END

    user_id = update.effective_user.id
    
    # Yangi testni boshlash, eski ma'lumotlarni o'chirish
    delete_user_data_from_db(user_id) 
    save_user_data_to_db(user_id, 0, 0) # Yangi test holatini saqlash (index=0, score=0)
    
    await update.message.reply_text("Test boshlandi!")
    # Birinchi savolni yuborish uchun ask_question ni chaqiramiz
    return await ask_question(update, context) # start_testdan keyin darhol savol berish

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Joriy savolni foydalanuvchiga yuboradi (yangi xabar sifatida)."""
    user_id = update.effective_user.id
    user_info = get_user_data_from_db(user_id)

    if not user_info:
        # Agar CallbackQuery dan kelsa
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text("Xato: Test holati topilmadi. Iltimos, /test ni qayta bosing.")
        else: # Agar oddiy Message dan kelsa
            await update.message.reply_text("Xato: Test holati topilmadi. Iltimos, /test ni qayta bosing.")
        return ConversationHandler.END

    current_index = user_info["current_question_index"]

    if current_index < len(tests_data):
        question_data = tests_data[current_index]
        question_text = f"Savol {current_index + 1}: {question_data['savol']}"
        
        keyboard = []
        for option in question_data['variantlar']:
            keyboard.append([InlineKeyboardButton(option, callback_data=option)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Har doim yangi xabar sifatida yuboramiz
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.message.reply_text(question_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(question_text, reply_markup=reply_markup)
        
        return ANSWERING
    else:
        # Test tugashi va natija
        final_score = user_info['score']
        total_questions = len(tests_data)
        
        message_to_reply = None
        if hasattr(update, 'callback_query') and update.callback_query:
            message_to_reply = update.callback_query.message
        elif hasattr(update, 'message') and update.message:
            message_to_reply = update.message
        
        if message_to_reply:
            await message_to_reply.reply_text(f"Test tugadi! Siz {final_score} / {total_questions} ball to'pladingiz.")
            await message_to_reply.reply_text("Yana biror narsa qilasizmi? /start")
        else:
            logger.error("ask_question: Tugatish xabarini yuborish uchun update obyekti topilmadi.")

        delete_user_data_from_db(user_id)
        
        return ConversationHandler.END

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Foydalanuvchi tugma orqali yuborgan javobini tekshiradi (CallbackQuery)."""
    query = update.callback_query
    await query.answer() # Queryni javob bergan deb belgilash, yuklanishni to'xtatadi

., [17.06.2025 0:55]
user_id = query.from_user.id
    user_answer = query.data # Tugmadagi callback_data

    user_info = get_user_data_from_db(user_id)
    if not user_info:
        await query.edit_message_text("Xato: Test holati topilmadi. Iltimos, testni qayta boshlang /test.")
        return ConversationHandler.END

    current_index = user_info["current_question_index"]
    score = user_info["score"]

    if current_index >= len(tests_data):
        await query.edit_message_text("Test allaqachon tugagan. Yangisini boshlash uchun /test.")
        delete_user_data_from_db(user_id)
        return ConversationHandler.END

    question_data = tests_data[current_index]
    correct_answer = question_data["togri_javob"]
    
    feedback_message = ""
    if user_answer == correct_answer:
        score += 1
        feedback_message = "✅ To'g'ri javob!"
    else:
        feedback_message = f"❌ Noto'g'ri javob. To'g'risi: {correct_answer}"
    
    # Javob berilgan xabardagi tugmalarni olib tashlash va javobni ko'rsatish
    # Bu, foydalanuvchi bir savolga ikki marta javob bera olmasligini ta'minlaydi.
    try:
        await query.edit_message_reply_markup(reply_markup=None) # Tugmalarni olib tashlash
        await query.edit_message_text(f"{query.message.text}\n\n{feedback_message}") # Oldingi savol matnini yangilash
    except Exception as e:
        logger.error(f"Xabarni tahrirlashda xato: {e}")
        await query.message.reply_text(feedback_message) # Agar tahrirlashda xato bo'lsa, yangi xabar yuborish

    current_index += 1
    save_user_data_to_db(user_id, current_index, score)
    
    await asyncio.sleep(0.7) # Javobni o'qib olishi uchun biroz kutish

    # Keyingi savolni yuborish
    return await ask_question(update, context) # Yangi savolni yuborish

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Suhbatni bekor qiladi."""
    user_id = update.effective_user.id
    delete_user_data_from_db(user_id)
    await update.message.reply_text("Test bekor qilindi. Yana biror narsa qilasizmi? /start")
    return ConversationHandler.END

# --- Umumiy xato handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botdagi barcha xatolarni qayta ishlaydi."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    # try:
    #     if update.callback_query:
    #         await update.callback_query.message.reply_text("Kechirasiz, kutilmagan xato yuz berdi. Iltimos, /start ni bosing.")
    #     elif update.message:
    #         await update.message.reply_text("Kechirasiz, kutilmagan xato yuz berdi. Iltimos, /start ni bosing.")
    # except Exception as e:
    #     logger.error(f"Xato xabarini yuborishda xato: {e}")


# --- Main funksiyasi (Botni ishga tushirish) ---
def main() -> None:
    """Botni ishga tushiradi."""
    # Bot tokenini muhit o'zgaruvchisidan olish
    TOKEN = os.environ.get("7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg") 
    if not TOKEN:
        # Agar muhit o'zgaruvchisi o'rnatilmagan bo'lsa, bu yerga tokeningizni qo'ying (tavsiya etilmaydi, faqat test uchun)
        logger.warning("BOT_TOKEN muhit o'zgaruvchisi topilmadi. Kod ichidagi token ishlatiladi.")
        TOKEN = "7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg" # TOKENNI BU YERGA QO'YING!
        
    if TOKEN == "7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg":
        logger.error("Iltimos, bot tokenini BOT_TOKEN muhit o'zgaruvchisi sifatida sozlang yoki kodga yozing!")
        exit(1)

    # Ma'lumotlar bazasini ishga tushirish
    init_db()
    # Exceldan test savollarini yuklash
    load_tests_from_excel(EXCEL_FILE_PATH)

    application = Application.builder().token(7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg).build()

    # ConversationHandler ni qo'shish
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("test", start_test)],

., [17.06.2025 0:55]
states={
            # CHOOSING_TEST holatida /test buyrug'ini qabul qilamiz
            CHOOSING_TEST: [CommandHandler("test", start_test)],
            # ANSWERING holatida tugmalardan kelgan javoblarni qayta ishlaymiz
            ANSWERING: [CallbackQueryHandler(handle_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True, # Har bir foydalanuvchi uchun alohida suhbat holatini boshqarish
        # per_chat=True, # Agar har bir chat uchun alohida holat kerak bo'lsa
    )
    application.add_handler(conv_handler)

    # --- Qo'shimcha handlerlar (agar kerak bo'lsa) ---
    # Matnli xabarlar uchun (agar testdan tashqarida bo'lsa)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start)) # Har qanday matnga start xabarini berish

    # Xato handler
    application.add_error_handler(error_handler)

    logger.info("Bot ishga tushirilmoqda (polling rejimida)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if name == "main":
    main()
