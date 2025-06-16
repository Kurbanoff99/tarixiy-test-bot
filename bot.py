import logging
import os
import openpyxl
import asyncio
import json # Firestore credentials uchun

# Firebase Admin SDK importlari
import firebase_admin
from firebase_admin import credentials, firestore

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

# --- Loglarni sozlash / Configure Logging ---
# Botning ish jarayonini kuzatish uchun loglashni sozlaymiz.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Holatlarni aniqlash / Define States ---
# Foydalanuvchi bilan suhbat holatlarini belgilaymiz.
CHOOSING_TEST, ANSWERING = range(2)

# --- Global o'zgaruvchilar / Global Variables ---
# Firestore client va app_id ni global qilib e'lon qilamiz.
db = None
APP_ID = None # Canvas yoki muhit o'zgaruvchisidan olinadi

# --- Firestore funksiyalari / Firestore Functions ---
# Foydalanuvchilarning testdagi holatini Firestore'da saqlash uchun.

def init_firestore():
    """Firebase va Firestore'ni ishga tushirish."""
    """Initialize Firebase and Firestore."""
    global db, APP_ID

    # APP_ID ni muhit o'zgaruvchisidan olishga harakat qilamiz, aks holda default ishlatamiz.
    # Canvas muhitida __app_id avtomatik tarzda berilishi mumkin.
    # Try to get APP_ID from environment variable, otherwise use default.
    # In Canvas environment, __app_id might be provided automatically.
    APP_ID = os.environ.get("APP_ID", "default-telegram-test-bot-app")

    # Firebase service account credentialsni olish.
    # Bu json fayl yo'li bo'lishi yoki to'g'ridan-to'g'ri json kontenti bo'lishi mumkin.
    # Get Firebase service account credentials.
    # This can be a path to a json file or direct json content.
    try:
        service_account_info_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
        if service_account_info_str:
            # Agar JSON string sifatida berilgan bo'lsa
            cred = credentials.Certificate(json.loads(service_account_info_str))
        else:
            # Agar fayl yo'li sifatida berilgan bo'lsa (masalan, GOOGLE_APPLICATION_CREDENTIALS)
            cred = credentials.ApplicationDefault()
        
        if not firebase_admin._apps: # Agar Firebase hali ishga tushirilmagan bo'lsa
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firestore muvaffaqiyatli ishga tushirildi.")
    except Exception as e:
        logger.error(f"Firestore ishga tushirishda xato: {e}")
        logger.error("Iltimos, FIREBASE_SERVICE_ACCOUNT_KEY muhit o'zgaruvchisi to'g'ri o'rnatilganligini tekshiring.")
        db = None # Ishga tushirish muvaffaqiyatsiz bo'lsa, db ni None ga o'rnatamiz

def get_user_data_from_db(user_id):
    """Foydalanuvchining ma'lumotlarini Firestore'dan olish."""
    """Retrieve user data from Firestore."""
    if not db:
        logger.error("Firestore ishga tushirilmagan. Ma'lumotlarni olish imkonsiz.")
        return None
    
    # Ma'lumotlar bazasi yo'li: /artifacts/{appId}/users/{userId}/test_progress/user_state
    doc_ref = db.collection('artifacts').document(APP_ID).collection('users').document(str(user_id)).collection('test_progress').document('user_state')
    
    try:
        doc = doc_ref.get()
        if doc.exists:
            logger.info(f"Foydalanuvchi {user_id} ma'lumotlari Firestore'dan olindi.")
            return doc.to_dict()
        else:
            logger.info(f"Foydalanuvchi {user_id} uchun ma'lumot topilmadi.")
            return None
    except Exception as e:
        logger.error(f"Foydalanuvchi {user_id} ma'lumotlarini olishda xato: {e}")
        return None

def save_user_data_to_db(user_id, current_question_index, score, current_test_file='test_savollar.xlsx'):
    """Foydalanuvchining ma'lumotlarini Firestore'ga saqlash yoki yangilash."""
    """Save or update user data in Firestore."""
    if not db:
        logger.error("Firestore ishga tushirilmagan. Ma'lumotlarni saqlash imkonsiz.")
        return
    
    doc_ref = db.collection('artifacts').document(APP_ID).collection('users').document(str(user_id)).collection('test_progress').document('user_state')
    
    user_data = {
        "current_question_index": current_question_index,
        "score": score,
        "current_test_file": current_test_file
    }
    try:
        doc_ref.set(user_data) # set() merge=True bilan yangilaydi yoki yaratadi
        logger.info(f"Foydalanuvchi {user_id} ma'lumotlari Firestore'ga saqlandi.")
    except Exception as e:
        logger.error(f"Foydalanuvchi {user_id} ma'lumotlarini saqlashda xato: {e}")

def delete_user_data_from_db(user_id):
    """Foydalanuvchining ma'lumotlarini Firestore'dan o'chirish."""
    """Delete user data from Firestore."""
    if not db:
        logger.error("Firestore ishga tushirilmagan. Ma'lumotlarni o'chirish imkonsiz.")
        return
        
    doc_ref = db.collection('artifacts').document(APP_ID).collection('users').document(str(user_id)).collection('test_progress').document('user_state')
    
    try:
        doc_ref.delete()
        logger.info(f"Foydalanuvchi {user_id} ma'lumotlari Firestore'dan o'chirildi.")
    except Exception as e:
        logger.error(f"Foydalanuvchi {user_id} ma'lumotlarini o'chirishda xato: {e}")

# --- Exceldan savollarni yuklash / Load Questions from Excel ---
def load_tests_from_excel(file_path):
    """Excel faylidan test savollarini yuklash."""
    """Load test questions from an Excel file."""
    local_tests_data = [] 

    if not os.path.exists(file_path):
        logger.error(f"Excel fayli topilmadi: {file_path}. Iltimos, fayl yo'lini tekshiring.")
        return []

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

            if question and correct_answer: 
                options = [opt for opt in [option_a, option_b, option_c, option_d] if opt is not None]
                local_tests_data.append({
                    "savol": str(question).strip(),
                    "variantlar": [str(o).strip() for o in options],
                    "togri_javob": str(correct_answer).strip()
                })
        logger.info(f"'{file_path}' faylidan {len(local_tests_data)} ta savol muvaffaqiyatli yuklandi.")
        return local_tests_data
    except Exception as e:
        logger.error(f"Excel yuklashda xato yuz berdi ('{file_path}'): {e}. Fayl formatini tekshiring.")
        return []

# --- Bot funksiyalari / Bot Handler Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bot /start buyrug'ini qabul qilganda javob beradi."""
    user = update.effective_user
    await update.message.reply_html(
        f"Salom, {user.mention_html()}! 👋 Testni boshlash uchun /test buyrug'ini bosing.\n"
        f"Yoki aniq bir test faylini ko'rsatish uchun: `/test fayl_nomi.xlsx`\n"
        f"Masalan: `/test biologiya.xlsx`"
    )
    return CHOOSING_TEST

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Testni boshlash buyrug'ini (odatda /test) qabul qilganda ishga tushadi."""
    user_id = update.effective_user.id
    
    excel_filename = "test_savollar.xlsx" 
    if context.args:
        excel_filename = context.args[0]
        if not excel_filename.lower().endswith('.xlsx'):
            excel_filename += '.xlsx' 
    
    current_tests_data = load_tests_from_excel(excel_filename)

    if not current_tests_data:
        msg = f"'{excel_filename}' test savollari yuklanmadi. Iltimos, fayl nomini va uning tarkibini tekshiring, yoki administrator bilan bog'laning."
        await (update.message.reply_text(msg)
               if update.message else update.callback_query.message.reply_text(msg))
        return ConversationHandler.END

    context.user_data['tests_data'] = current_tests_data
    context.user_data['current_test_file'] = excel_filename

    delete_user_data_from_db(user_id) # Oldingi test ma'lumotlarini o'chirib tashlaymiz
    save_user_data_to_db(user_id, 0, 0, excel_filename) # Yangi test uchun holatni Firestore'ga saqlaymiz

    await (update.message.reply_text(f"'{excel_filename}' test boshlandi! Omad tilaymiz! 💪")
           if update.message else update.callback_query.message.reply_text(f"'{excel_filename}' test boshlandi! Omad tilaymiz! 💪"))
    return await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Navbatdagi test savolini foydalanuvchiga yuboradi."""
    user_id = update.effective_user.id
    user_info = get_user_data_from_db(user_id)

    if not user_info:
        await (update.message.reply_text("Xato: Test holati topilmadi. /test buyrug'ini qayta bosing.")
               if update.message else update.callback_query.message.reply_text("Xato: Test holati topilmadi. /test buyrug'ini qayta bosing."))
        return ConversationHandler.END
    
    current_test_file = user_info.get("current_test_file", "test_savollar.xlsx")
    current_tests_data = context.user_data.get('tests_data')
    if not current_tests_data or context.user_data.get('current_test_file') != current_test_file:
        current_tests_data = load_tests_from_excel(current_test_file)
        if not current_tests_data:
            msg = f"Oldingi test fayli ('{current_test_file}') topilmadi yoki yuklanmadi. Iltimos, /test buyrug'i bilan yangi testni boshlang."
            await (update.message.reply_text(msg)
                   if update.message else update.callback_query.message.reply_text(msg))
            delete_user_data_from_db(user_id)
            return ConversationHandler.END
        context.user_data['tests_data'] = current_tests_data
        context.user_data['current_test_file'] = current_test_file


    current_index = user_info["current_question_index"]

    if current_index < len(current_tests_data):
        question_data = current_tests_data[current_index]
        question_text = f"Savol {current_index + 1}/{len(current_tests_data)}:\n\n{question_data['savol']}"

        keyboard = [
            [InlineKeyboardButton(option, callback_data=option)]
            for option in question_data['variantlar']
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            try:
                await update.callback_query.message.edit_text(question_text, reply_markup=reply_markup)
            except Exception as e:
                logger.warning(f"Oldingi savol xabarini tahrirlashda xato: {e}. Yangi xabar yuborilmoqda.")
                await update.callback_query.message.reply_text(question_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(question_text, reply_markup=reply_markup)

        return ANSWERING
    else:
        final_score = user_info["score"]
        total_questions = len(current_tests_data)
        msg = (f"Test yakunlandi! 🎉 Siz {total_questions} ta savoldan "
               f"{final_score} ta to'g'ri javob to'pladingiz.\n\n"
               f"/test buyrug'i orqali qayta boshlashingiz mumkin.")

        if update.callback_query:
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)

        delete_user_data_from_db(user_id)
        return ConversationHandler.END

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Foydalanuvchi javobini (inline tugma bosilganda) qayta ishlaydi."""
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
    current_test_file = user_info["current_test_file"]

    current_tests_data = context.user_data.get('tests_data')
    if not current_tests_data or context.user_data.get('current_test_file') != current_test_file:
        current_tests_data = load_tests_from_excel(current_test_file)
        if not current_tests_data:
            msg = f"Oldingi test fayli ('{current_test_file}') topilmadi yoki yuklanmadi. Iltimos, /test buyrug'i bilan yangi testni boshlang."
            await query.message.reply_text(msg)
            delete_user_data_from_db(user_id)
            return ConversationHandler.END
        context.user_data['tests_data'] = current_tests_data
        context.user_data['current_test_file'] = current_test_file


    if current_index >= len(current_tests_data):
        await query.edit_message_text("Test allaqachon tugagan. /test buyrug'i orqali qaytadan boshlashingiz mumkin.")
        delete_user_data_from_db(user_id)
        return ConversationHandler.END

    question_data = current_tests_data[current_index]
    correct_answer = question_data["togri_javob"]

    feedback_emoji = "✅" if user_answer == correct_answer else "❌"
    feedback_text = f"Sizning javobingiz: *{user_answer}*"
    if user_answer != correct_answer:
        feedback_text += f"\nTo'g'ri javob: *{correct_answer}*"

    try:
        await query.edit_message_text(
            f"{query.message.text}\n\n{feedback_emoji} {feedback_text}",
            parse_mode='Markdown' 
        )
    except Exception as e:
        logger.error(f"Xabarni yangilashda xato: {e}. Yangi xabar yuborilmoqda.")
        await query.message.reply_text(f"{feedback_emoji} {feedback_text}", parse_mode='Markdown')

    if user_answer == correct_answer:
        score += 1

    current_index += 1
    save_user_data_to_db(user_id, current_index, score, current_test_file)

    await asyncio.sleep(0.7)

    return await ask_question(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Testni bekor qiladi va suhbatni tugatadi."""
    user_id = update.effective_user.id
    delete_user_data_from_db(user_id)
    await update.message.reply_text("Test bekor qilindi. Boshqa testni boshlash uchun /test buyrug'ini bosing.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Botda yuzaga kelgan xatolarni qayd etadi."""
    logger.warning('Xato: "%s" - "%s"', update, context.error)

# --- Botni ishga tushirish / Run the Bot ---

def main():
    """Botni ishga tushirish uchun asosiy funksiya."""
    TOKEN = os.environ.get("7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg") 
    if not TOKEN:
        logger.error("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan. Iltimos, .env faylini yoki muhit o'zgaruvchisini tekshiring.")
        return

    init_firestore() # Firestore'ni ishga tushiramiz

    if db is None: # Agar Firestore ishga tushirilmagan bo'lsa, chiqib ketamiz
        logger.critical("Firestore ga ulanish muvaffaqiyatsiz tugadi. Bot ishga tushirilmaydi.")
        return

    application = Application.builder().token(TOKEN).build()

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

    logger.info("Bot ishga tushirildi va yangilanishlarni kutmoqda...")
    application.run_polling()

if __name__ == "__main__":
    main()
