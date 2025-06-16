import logging
import os
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

# Logging
logging.basicConfig(level=logging.INFO)

# Foydalanuvchi holati uchun global o'zgaruvchilar
user_states = {}
TEST_DIR = "tests"

# Bosqichlar
(START_TEST, ANSWERING) = range(2)

# Excel fayldan savollarni yuklaymiz
def load_questions(filename):
    df = pd.read_excel(filename)
    return df.to_dict('records')

# /start komandasi\async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {
        "test_files": sorted([f for f in os.listdir(TEST_DIR) if f.endswith(".xlsx")]),
        "current_file": 0,
        "current_question": 0,
        "correct_answers": 0,
        "questions": []
    }
    await update.message.reply_text("Assalomu alaykum! Tarixiy test botiga xush kelibsiz!\nBoshlash uchun /test buyrug‘ini bering.")

# /test komandasi
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states[user_id]

    if state["current_file"] >= len(state["test_files"]):
        await update.message.reply_text("Barcha testlar tugadi. Rahmat!")
        return ConversationHandler.END

    file_path = os.path.join(TEST_DIR, state["test_files"][state["current_file"]])
    state["questions"] = load_questions(file_path)
    state["current_question"] = 0
    state["correct_answers"] = 0

    return await ask_question(update, context)

# Savolni chiqarish
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states[user_id]
    questions = state["questions"]

    if state["current_question"] >= len(questions):
        await update.message.reply_text(f"Test tugadi. To‘g‘ri javoblar soni: {state['correct_answers']} / {len(questions)}")
        state["current_file"] += 1
        return await start_test(update, context)

    q = questions[state["current_question"]]
    variants = [q['variant_a'], q['variant_b'], q['variant_c']]
    markup = ReplyKeyboardMarkup([["A", "B", "C"]], one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(f"{q['savol']}\nA) {q['variant_a']}\nB) {q['variant_b']}\nC) {q['variant_c']}", reply_markup=markup)
    return ANSWERING

# Javobni tekshirish
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states[user_id]
    answer = update.message.text.strip().upper()

    q = state["questions"][state["current_question"]]
    if answer == q['togrijavob'].strip().upper():
        state["correct_answers"] += 1

    state["current_question"] += 1
    return await ask_question(update, context)

# Botni ishga tushurish
if __name__ == '__main__':
    from telegram.ext import ApplicationBuilder
    TOKEN = "YOUR_BOT_TOKEN"

    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("test", start_test)],
        states={
            ANSWERING: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    app.run_polling()
