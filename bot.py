import os
import random
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Tokenni o'zgaruvchi orqali olish (render.com uchun)
TOKEN = os.getenv("7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg")  # Agar lokalda ishlayotgan bo‘lsangiz: TOKEN = "TOKEN_BU_YERGA"

# 📥 Excel fayldan testlarni o‘qish
def load_tests_from_excel(file_name="testlar.xlsx"):
    try:
        df = pd.read_excel(file_name)
        testlar = []
        for _, row in df.iterrows():
            testlar.append({
                "savol": row["savol"],
                "variantlar": [row["variant1"], row["variant2"], row["variant3"], row["variant4"]],
                "togri": row["togri"]
            })
        return testlar
    except Exception as e:
        print(f"Xatolik: Exceldan testlarni o‘qishda muammo: {e}")
        return []

# 📚 Testlar ro‘yxatini yuklab olish
testlar = load_tests_from_excel()

# ▶️ /start buyrug‘i
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Tarixiy test uchun /test deb yozing.")

# ▶️ /test buyrug‘i
async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not testlar:
        await update.message.reply_text("Testlar topilmadi. Iltimos, testlar.xlsx faylini tekshiring.")
        return

    savol = random.choice(testlar)
    context.user_data["savol"] = savol

    markup = ReplyKeyboardMarkup([[v] for v in savol["variantlar"]],
                                 one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(savol["savol"], reply_markup=markup)

# ✅ Javobni tekshirish
async def javob_tekshir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    javob = update.message.text
    savol = context.user_data.get("savol")

    if not savol:
        await update.message.reply_text("Avval /test deb yozing.")
        return

    if javob == savol["togri"]:
        await update.message.reply_text("✅ To‘g‘ri javob!")
    else:
        await update.message.reply_text(f"❌ Noto‘g‘ri. To‘g‘ri javob: {savol['togri']}")

# 🚀 Botni ishga tushurish
app = ApplicationBuilder().token("7775497614:AAFRrodSyDotYX0AMIG7o0ijMXXizcSsbxg").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("test", test))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, javob_tekshir))
app.run_polling()
