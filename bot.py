import os
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Global o'zgaruvchilar
user_data = {}
TEST_PATH = "tests"
(ANSWER,) = range(1)

# Savollarni yuklovchi funksiya
def load_questions(filename):
    df = pd.read_excel(filename)
    return df.to_dict("records")

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = sorted([f for f in os.listdir(TEST_PATH) if f.endswith(".xlsx")])
    user_data[user_id] = {
        "files": files,
        "current_file": 0,
        "questions": [],
        "current_question": 0,
        "correct": 0
    }
    await update.message.reply_text("Assalomu alaykum! Testni boshlash uchun /test buyrug'ini bering.")

# /test komandasi
async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]

    if data["current_file"] >= len(data["files"]):
        await update.message.reply_text("Barcha testlar tugadi.")
        return ConversationHandler.END

    filepath = os.path.join(TEST_PATH, data["files"][data["current_file"]])
    data["questions"] = load_questions(filepath)
    data["current_question"] = 0
    data["correct"] = 0
    return await ask_question(update)

# Savol yuborish
async def ask_question(update: Update):
    user_id = update.effective_user.id
    data = user_data[user_id]

    if data["current_question"] >= len(data["questions"]):
        msg = f"Test tugadi. To'g'ri javoblar: {data['correct']}/{len(data['questions'])}"
        await update.message.reply_text(msg)
        data["current_file"] += 1
        return await start_test(update, None)

    q = data["questions"][data["current_question"]]
    text = f"{q['savol']}\nA) {q['variant_a']}\nB) {q['variant_b']}\nC) {q['variant_c']}"
    markup = ReplyKeyboardMarkup([["A", "B", "C"]], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(text, reply_markup=markup)
    return ANSWER

# Javobni tekshirish
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    user_answer = update.message.text.strip().upper()
    correct_answer = data["questions"][data["current_question"]]["togrijavob"].strip().upper()

    if user_answer == correct_answer:
        data["correct"] += 1

    data["current_question"] += 1
    return await ask_question(update)

# Asosiy
if __name__ == "__main__":
    TOKEN = "7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg"  # <-- tokenni shu yerga qo‘ying

    app = ApplicationBuilder().token("7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg").build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("test", start_test)],
        states={
            ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.run_polling()
