from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os

TOKEN = os.getenv("BOT_TOKEN")

savol = "Amir Temur qachon tug‘ilgan?"
variantlar = ["1225", "1336", "1405", "1500"]
togri_javob = "1336"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Tarixiy test uchun /test buyrug‘ini yozing.")

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = ReplyKeyboardMarkup([[v] for v in variantlar], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(savol, reply_markup=markup)

async def javob_tekshir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    javob = update.message.text
    if javob == togri_javob:
        await update.message.reply_text("✅ To‘g‘ri!")
    else:
        await update.message.reply_text(f"❌ Noto‘g‘ri. To‘g‘ri javob: {togri_javob}")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("test", test))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, javob_tekshir))

app.run_polling()
