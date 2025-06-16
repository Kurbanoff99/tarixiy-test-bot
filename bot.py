import logging
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Foydalanuvchi holati (test holati)
user_states = {}

# Excel fayldan savollarni o‘qish funksiyasi
def load_test(filename):
    df = pd.read_excel(filename)
    questions = []
    for _, row in df.iterrows():
        questions.append({
            'savol': row['Savol'],
            'varianti': [row['A'], row['B'], row['C'], row['D']],
            'javob': row['To‘g‘ri javob']
        })
    return questions

# Test fayli
test = load_test("test1.xlsx")

# /start buyrug‘i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {'index': 0, 'ball': 0}
    await send_question(update, context)

# Savolni yuborish
async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states.get(user_id)

    if state and state['index'] < len(test):
        q = test[state['index']]
        buttons = [
            [InlineKeyboardButton(q['varianti'][0], callback_data='A')],
            [InlineKeyboardButton(q['varianti'][1], callback_data='B')],
            [InlineKeyboardButton(q['varianti'][2], callback_data='C')],
            [InlineKeyboardButton(q['varianti'][3], callback_data='D')],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await context.bot.send_message(chat_id=user_id, text=f"{state['index'] + 1}-savol:\n{q['savol']}", reply_markup=reply_markup)
    else:
        score = state['ball']
        await context.bot.send_message(chat_id=user_id, text=f"Test tugadi!\nTo‘plagan balingiz: {score} / {len(test)}")
        del user_states[user_id]

# Tugma bosilganda
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    state = user_states.get(user_id)
    if state is None:
        return

    current_question = test[state['index']]
    selected = query.data
    correct = current_question['javob'].strip().upper()

    if selected == correct:
        state['ball'] += 1
        feedback = "✅ To‘g‘ri javob!"
    else:
        feedback = f"❌ Noto‘g‘ri. To‘g‘ri javob: {correct}"

    await query.edit_message_text(f"{current_question['savol']}\n\n{feedback}")
    state['index'] += 1
    await send_question(update, context)

# Botni ishga tushirish
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv("BOT_TOKEN") or "BOT_TOKEN_BU_YERGA"

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()
