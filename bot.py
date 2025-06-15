question_data = tests_data[current_index]
    correct_answer = question_data["togri_javob"]
    
    feedback_message = ""
    if user_answer == correct_answer:
        score += 1
        feedback_message = "✅ To'g'ri javob!"
    else:
        feedback_message = f"❌ Noto'g'ri javob. To'g'risi: {correct_answer}"
    
    # Foydalanuvchiga javob haqida qisqa ma'lumot berish
    await query.edit_message_text(f"{feedback_message}\n") # Javobni ko'rsatish
    
    current_index += 1
    save_user_data_to_db(user_id, current_index, score) # DB ga yangi holatni saqlash
    
    # Keyingi savolni yuborish uchun biroz kechikish
    # import asyncio
    # await asyncio.sleep(1) # Javobni o'qib olishi uchun 1 soniya kutish
    
    return await ask_question(update, context) # Keyingi savolni berish

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
    TOKEN = os.environ.get("BOT_TOKEN") 
    if not TOKEN:
        # Agar muhit o'zgaruvchisi o'rnatilmagan bo'lsa, bu yerga tokeningizni qo'ying (tavsiya etilmaydi, faqat test uchun)
        logger.warning("BOT_TOKEN muhit o'zgaruvchisi topilmadi. Kod ichidagi token ishlatiladi.")
        TOKEN = "Sizning_BotFather_Tokeningiz_Bu_Yerga" # TOKENNI BU YERGA QO'YING!
        
    if TOKEN == "Sizning_BotFather_Tokeningiz_Bu_Yerga":
        logger.error("Iltimos, bot tokenini BOT_TOKEN muhit o'zgaruvchisi sifatida sozlang yoki kodga yozing!")
        exit(1)

    # Ma'lumotlar bazasini ishga tushirish
    init_db()
    # Exceldan test savollarini yuklash
    load_tests_from_excel(EXCEL_FILE_PATH)

    application = Application.builder().token(TOKEN).build()

    # ConversationHandler ni qo'shish
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("test", start_test)],
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
