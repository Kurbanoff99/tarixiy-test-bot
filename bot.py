import os
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

user_data = {}
TEST_PATH = "tests"
(ANSWER,) = range(1)

def load_questions(filename):
    df = pd.read_excel(filename)
    return df.to_dict("records")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    files = sorted([f for f in os.listdir(TEST_PATH) if f.endswith(".xlsx")])
    if not files:
        await update.message.reply_text("❌ Hech qanday test fayli topilmadi.")
        return
    user_data[user_id] = {
        "files": files,
        "current_file": 0,
        "questions": [],
        "current_question": 0,
        "correct": 0
    }
    await update.message.reply_text("Assalomu alaykum!\nTestni boshlash uchun /test buyrug‘ini yuboring.")

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    if data["current_file"] >= len(data["files"]):
        await update.message.reply_text("✅ Barcha testlar tugadi.")
        return ConversationHandler.END

    filename = os.path.join(TEST_PATH, data["files"][data["current_file"]])
    data["questions"] = load_questions(filename)
    data["current_question"] = 0
    data["correct"] = 0

    return await ask_question(update)

async def ask_question(update: Update):
    user_id = update.effective_user.id
    data = user_data[user_id]
    if data["current_question"] >= len(data["questions"]):
        msg = f"✅ To‘g‘ri javoblar soni: {data['correct']}/{len(data['questions'])}"
        await update.message.reply_text(msg)
        data["current_file"] += 1
        return await start_test(update, None)

    q = data["questions"][data["current_question"]]
    text = f"{q['savol']}\n\nA) {q['variant_a']}\nB) {q['variant_b']}\nC) {q['variant_c']}"
    markup = ReplyKeyboardMarkup([["A", "B", "C"]], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(text, reply_markup=markup)
    return ANSWER

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_data[user_id]
    user_answer = update.message.text.strip().upper()
    correct_answer = data["questions"][data["current_question"]]["togrijavob"].strip().upper()

    if user_answer == correct_answer:
        data["correct"] += 1

    data["current_question"] += 1
    return await ask_question(update)

if __name__ == "__main__":
    app = ApplicationBuilder().token("TOKENINGIZNI_BU_YERGA_QO‘YING").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("test", start_test)],
        states={ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer)]},
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    app.run_polling()
