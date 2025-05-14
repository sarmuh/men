import logging
import random
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from savol import questions  # savol.py faylidan questions ro'yxatini import qilish

# Logging sozlamalari
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Asosiy menyuni inline klaviatura sifatida ko‘rsatish
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🚀 Bosh Menyu", callback_data="/start"), InlineKeyboardButton("🤝 Yordam", callback_data="/help")],
        [InlineKeyboardButton("🧠 Testni boshlash", callback_data="/quiz"), InlineKeyboardButton("📊 Statistika", callback_data="/stats")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Start buyrug‘i: KI guruhiga xush kelibsiz xabari
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name if user.first_name else user.username if user.username else "Foydalanuvchi"
    welcome_message = (
        f"🇺🇿 Assalomu alaykum, {user_name}! KI guruhi a'zolari uchun Dinshunoslik fanidan yakuniy imtihonga tayyorlanish botiga xush kelibsiz! 🎓\n\n"
        "🔹 25 ta tasodifiy savoldan iborat test boshlash uchun Testni boshlash tugmasiga bosing\n"
    )
    query = update.callback_query
    if query:
        await query.message.reply_text(welcome_message, reply_markup=get_main_menu())
    else:
        await update.message.reply_text(welcome_message, reply_markup=get_main_menu())

# Yordam buyrug‘i
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = (
        "📚 Bot yordami:\n\n"
        "🔹 /start - Botni qayta ishga tushirish va xush kelibsiz xabarini ko‘rish\n"
        "🔹 /quiz - 25 ta tasodifiy savoldan iborat test boshlash\n"
        "🔹 /stats - Umumiy statistikangizni ko‘rish\n\n"
        "Bot faqat kiritilgan 400 ta savoldan foydalanadi va har doim tasodifiy tartibda taqdim etadi."
    )
    query = update.callback_query
    if query:
        await query.message.reply_text(help_message, reply_markup=get_main_menu())
    else:
        await update.message.reply_text(help_message, reply_markup=get_main_menu())

# Statistika buyrug‘i
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data.get('stats', {'tests': 0, 'total_correct': 0, 'best_score': 0})
    tests = user_data['tests']
    total_correct = user_data['total_correct']
    best_score = user_data['best_score']
    
    if tests == 0:
        message = "📊 Hozircha hech qanday statistika yo‘q. /quiz orqali testni boshlang!"
    else:
        avg_score = (total_correct / (tests * 25)) * 100 if tests > 0 else 0
        message = (
            f"📊 Sizning statistikangiz:\n\n"
            f"🔢 Jami testlar soni: {tests}\n"
            f"✅ Jami to‘g‘ri javoblar: {total_correct}/{(tests * 25)}\n"
            f"📈 O‘rtacha ball: {avg_score:.2f}%\n"
            f"🏆 Eng yaxshi natija: {best_score}/25\n\n"
            f"🔄 Yana sinab ko‘rish uchun Testni boshlashni ni bosing!"
        )
    
    query = update.callback_query
    if query:
        await query.message.reply_text(message, reply_markup=get_main_menu())
    else:
        await update.message.reply_text(message, reply_markup=get_main_menu())

# Quiz buyrug‘i: 25 ta savol
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(questions) < 25:
        message = "❌ Savollar ro'yxati yetarli emas. Iltimos, savollar faylini tekshiring."
        query = update.callback_query
        if query:
            await query.message.reply_text(message, reply_markup=get_main_menu())
        else:
            await update.message.reply_text(message, reply_markup=get_main_menu())
        return
    
    context.user_data['index'] = 0
    context.user_data['answers'] = []
    context.user_data['shuffled'] = random.sample(questions, 25)  # 25 ta savol
    query = update.callback_query
    if query:
        await query.message.reply_text("Quiz boshlandi!")
        await send_question(query.message, context)
    else:
        await update.message.reply_text("Quiz boshlandi!")
        await send_question(update.message, context)

# Taymerni to‘xtatish
def cancel_timer(context: ContextTypes.DEFAULT_TYPE):
    if 'timer_task' in context.user_data:
        context.user_data['timer_task'].cancel()
        del context.user_data['timer_task']

# Savol yuborish va taymerni boshlash
async def send_question(message, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data['index']
    if index >= 25:  # 25 ta savoldan keyin yakunlash
        correct = sum(1 for a in context.user_data['answers'] if a['is_correct'])
        percentage = (correct / 25) * 100
        summary = (
            f"🏁 Test yakunlandi! Natija: {correct}/25 ({percentage:.2f}%)\n\n"
            "📊 Statistika:\n"
            f"✅ To‘g‘ri javoblar: {correct}\n"
            f"❌ Noto‘g‘ri javoblar: {25 - correct}\n"
            f"📈 Foiz: {percentage:.2f}%\n\n"
            "📝 Har bir savol bo‘yicha xulosa:\n"
        )
        for i, a in enumerate(context.user_data['answers'], 1):
            summary += (
                f"{i}. {a['question']}\n"
                f"✅ To‘g‘ri javob: {a['correct'].split(') ')[1]}\n"
                f"{'✔️ Sizning javobingiz to‘g‘ri' if a['is_correct'] else f'❌ Sizning javobingiz: {a['user_answer']}'}\n\n"
            )
        summary += (
            "🔄 Yana sinab ko‘rish uchun /quiz buyrug‘ini yuboring!\n"
            "📊 Umumiy statistikani ko‘rish uchun /stats ni bosing."
        )

        # Statistika yangilash
        user_data = context.user_data.get('stats', {'tests': 0, 'total_correct': 0, 'best_score': 0})
        user_data['tests'] = user_data.get('tests', 0) + 1
        user_data['total_correct'] = user_data.get('total_correct', 0) + correct
        user_data['best_score'] = max(user_data.get('best_score', 0), correct)
        context.user_data['stats'] = user_data

        # Taymerni to‘xtatish
        cancel_timer(context)

        await message.reply_text(summary, reply_markup=get_main_menu())
        return

    question = context.user_data['shuffled'][index]
    context.user_data['current_question'] = question
    lines = question.strip().split('\n')
    text = lines[0]
    options = lines[1:]

    # Variantlarni aralashtirish
    correct_option = next(opt for opt in options if opt.startswith('*'))
    correct_answer = correct_option.strip('*')[0]  # To‘g‘ri javob harfi
    options_data = [(opt.strip('*')[2:].strip(), opt.startswith('*')) for opt in options]  # Harf va * olib tashlanadi
    random.shuffle(options_data)  # Har safar variantlarni aralashtirish
    context.user_data['current_options'] = options_data
    context.user_data['correct_answer'] = correct_answer

    # Inline klaviatura tugmalarini yaratish
    keyboard = [[InlineKeyboardButton(opt[0], callback_data=f"answer_{i}")] for i, opt in enumerate(options_data)]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        # Savolni yuborish va xabar ID sini saqlash
        sent_message = await message.reply_text(
            f"❓ Savol {index + 1}/25:\n{text}\n\n⏰ 2 daqiqa vaqtingiz bor!",
            reply_markup=reply_markup
        )
        context.user_data['current_message_id'] = sent_message.message_id
        context.user_data['current_chat_id'] = sent_message.chat_id

        # Oldingi taymerni to‘xtatish
        cancel_timer(context)

        # Taymerni boshlash
        async def timer():
            try:
                await asyncio.sleep(120)  # 2 daqiqa (120 soniya)
                if 'current_question' in context.user_data:  # Savol hali faol bo‘lsa
                    # Savolni o‘chirish
                    try:
                        await context.bot.delete_message(
                            chat_id=context.user_data['current_chat_id'],
                            message_id=context.user_data['current_message_id']
                        )
                    except Exception as e:
                        logger.error(f"Xabarni o‘chirishda xato: {e}")

                    context.user_data['index'] += 1
                    context.user_data['answers'].append({
                        'question': text,
                        'correct': correct_option,
                        'is_correct': False,
                        'user_answer': "Vaqt tugadi"
                    })
                    await context.bot.send_message(
                        chat_id=context.user_data['current_chat_id'],
                        text="⏰ Vaqt tugadi! Keyingi savolga o‘tamiz."
                    )
                    await send_question(message, context)
            except asyncio.CancelledError:
                pass

        context.user_data['timer_task'] = asyncio.create_task(timer())
    except Exception as e:
        logger.error(f"Savol yuborishda xato: {e}")
        await message.reply_text("❌ Texnik xato yuz berdi. Iltimos, /quiz ni qayta ishlatib ko‘ring.", reply_markup=get_main_menu())

# Inline tugma bosilganda javob qayta ishlash
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data in ["/start", "/help", "/quiz", "/stats"]:
        # Inline menyudan buyruqlarni ishga tushirish
        if data == "/start":
            await start(update, context)
        elif data == "/help":
            await help_command(update, context)
        elif data == "/quiz":
            await quiz(update, context)
        elif data == "/stats":
            await stats(update, context)
        await query.answer()
        return

    if data.startswith("answer_") and 'current_question' in context.user_data:
        option_index = int(data.split("_")[1])
        user_answer = context.user_data['current_options'][option_index][0]
        is_correct = context.user_data['current_options'][option_index][1]
        question = context.user_data['current_question']
        correct_option = next(opt for opt in question.strip().split('\n')[1:] if opt.startswith('*'))
        correct_text = correct_option.split(') ')[1]

        # Taymerni to‘xtatish
        cancel_timer(context)

        # Javobni saqlash
        context.user_data['answers'].append({
            'question': question.strip().split('\n')[0],
            'correct': correct_option,
            'is_correct': is_correct,
            'user_answer': user_answer
        })
        context.user_data['index'] += 1

        # Foydalanuvchiga javob haqida xabar berish
        if is_correct:
            await query.message.reply_text("✅ To‘g‘ri javob! Keyingi savolga o‘ting.")
        else:
            await query.message.reply_text(f"❌ Noto‘g‘ri. To‘g‘ri javob: {correct_text}")

        await query.answer()
        await send_question(query.message, context)
    else:
        await query.message.reply_text("❓ Iltimos, avval /quiz buyrug‘ini ishlatib testni boshlang.", reply_markup=get_main_menu())
        await query.answer()

# Xato boshqaruvi
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} xato keltirib chiqardi: {context.error}")
    if update.message:
        await update.message.reply_text("❌ Xato yuz berdi. Iltimos, qaytadan urinib ko‘ring yoki /help ni bosing.", reply_markup=get_main_menu())
    elif update.callback_query:
        await update.callback_query.message.reply_text("❌ Xato yuz berdi. Iltimos, qaytadan urinib ko‘ring yoki /help ni bosing.", reply_markup=get_main_menu())

# Asosiy funksiya
def main():
    try:
        app = ApplicationBuilder().token("8013975637:AAHLHl1sqW2FU4MFM8Md8ko6cEAWB91JEwk").build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("quiz", quiz))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_error_handler(error_handler)
        
        logger.info("Bot muvaffaqiyatli ishga tushdi")
        app.run_polling()
    except Exception as e:
        logger.critical(f"Botni ishga tushirishda xato: {e}")

if __name__ == "__main__":
    main()