from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes
import os

TOKEN = os.getenv("7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg")

savollar = [
    {
        "savol": "Amir Temur qaysi yilda tug‘ilgan?",
        "variantlar": ["1336", "1402", "1220", "1389"],
        "togri": "1336"
    },
    {
        "savol": "O‘zbekiston mustaqillikka qachon erishgan?",
        "variantlar": ["1990", "1991", "1992", "1993"],
        "togri": "1991"
    },
    {
        "savol": "Buyuk Ipak Yo‘li qaysi qit'adan boshlanadi?",
        "variantlar": ["Osiyo", "Yevropa", "Afrika", "Avstraliya"],
        "togri": "Osiyo"
    }
]

# Foydalanuvchi holatini saqlash uchun lug'at
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Salom! Tarixiy test botiga xush kelibsiz.\n/test buyrug‘i bilan testni boshlang.")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = 0  # 0-indeksli savoldan boshlaymiz
    await send_question(update, user_states[user_id])

async def send_question(update: Update, question_index):
    savol = savollar[question_index]
    tugmalar = [
        [InlineKeyboardButton(text=variant, callback_data=f"javob|{question_index}|{variant}")]
        for variant in savol["variantlar"]
    ]
    markup = InlineKeyboardMarkup(tugmalar)
    if update.callback_query:
        await update.callback_query.message.edit_text(savol["savol"], reply_markup=markup)
    else:
        await update.message.reply_text(savol["savol"], reply_markup=markup)

async def tugma_javobi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    _, indeks, tanlov = query.data.split("|")
    indeks = int(indeks)
    togri = savollar[indeks]["togri"]

    if tanlov == togri:
        javob_matni = f"✅ To‘g‘ri javob! ({tanlov})"
    else:
        javob_matni = f"❌ Noto‘g‘ri. To‘g‘ri javob: {togri}"

    await query.edit_message_text(javob_matni)

    # Keyingi savolga o'tish
    user_states[user_id] = indeks + 1
    if user_states[user_id] < len(savollar):
        await send_question(update, user_states[user_id])
    else:
        await query.message.reply_text("🎉 Test yakunlandi! Rahmat.")

app = ApplicationBuilder().token("7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("test", test))
app.add_handler(CallbackQueryHandler(tugma_javobi))

print("🤖 Bot ishga tushdi...")
app.run_polling()
