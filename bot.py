import os
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from presentation_generator import PresentationGenerator
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
TOPIC, SLIDES, ADDITIONAL, CONFIRM = range(4)


class PresentationBot:
    def __init__(self):
        self.generator = PresentationGenerator()
        self.user_data = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 Привет! Я бот для генерации презентаций.\n"
            "Я помогу создать презентацию на любую тему.\n\n"
            "Для начала введите команду /generate"
        )

    async def generate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🎯 Введите тему для презентации:",
            reply_markup=ReplyKeyboardRemove()
        )
        return TOPIC

    async def get_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topic = update.message.text
        context.user_data['topic'] = topic

        await update.message.reply_text(
            f"📊 Тема: {topic}\n"
            f"Сколько слайдов должно быть в презентации? (по умолчанию {Config.DEFAULT_SLIDES}):"
        )
        return SLIDES

    async def get_slides(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            num_slides = int(update.message.text)
            if num_slides > Config.MAX_SLIDES:
                await update.message.reply_text(
                    f"⚠️ Максимальное количество слайдов: {Config.MAX_SLIDES}. "
                    f"Установлено значение {Config.MAX_SLIDES}."
                )
                num_slides = Config.MAX_SLIDES
        except ValueError:
            num_slides = Config.DEFAULT_SLIDES
            await update.message.reply_text(
                f"⚠️ Установлено значение по умолчанию: {num_slides} слайдов"
            )

        context.user_data['num_slides'] = num_slides

        await update.message.reply_text(
            "💡 Есть ли дополнительные пожелания к презентации?\n"
            "(например: 'больше примеров', 'акцент на данных', 'минимум текста')\n\n"
            "Или напишите 'нет', если дополнений нет:"
        )
        return ADDITIONAL

    async def get_additional(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        additional = update.message.text
        if additional.lower() in ['нет', 'no', '']:
            additional = ""

        context.user_data['additional'] = additional

        # Подтверждение
        topic = context.user_data['topic']
        num_slides = context.user_data['num_slides']
        additional_text = context.user_data['additional']

        confirmation_text = (
            f"✅ Подтвердите создание презентации:\n\n"
            f"🎯 Тема: {topic}\n"
            f"📊 Слайдов: {num_slides}\n"
        )

        if additional_text:
            confirmation_text += f"💡 Дополнения: {additional_text}\n"

        confirmation_text += "\nСоздаем презентацию?"

        keyboard = [['✅ Да', '❌ Нет']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

        await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
        return CONFIRM

    async def confirm_generation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_choice = update.message.text

        if user_choice == '✅ Да':
            await update.message.reply_text(
                "🔄 Генерирую презентацию... Это может занять несколько минут.",
                reply_markup=ReplyKeyboardRemove()
            )

            try:
                # Генерация презентации
                topic = context.user_data['topic']
                num_slides = context.user_data['num_slides']
                additional = context.user_data['additional']

                file_path = self.generator.generate_presentation(topic, num_slides, additional)

                if file_path and os.path.exists(file_path):
                    # Отправка файла пользователю
                    with open(file_path, 'rb') as file:
                        await update.message.reply_document(
                            document=file,
                            filename=os.path.basename(file_path),
                            caption="🎉 Ваша презентация готова!"
                        )
                    # Удаляем временный файл
                    os.remove(file_path)
                else:
                    await update.message.reply_text("❌ Произошла ошибка при генерации презентации.")

            except Exception as e:
                logger.error(f"Error generating presentation: {e}")
                await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")

        else:
            await update.message.reply_text(
                "Создание презентации отменено. Для начала заново введите /generate",
                reply_markup=ReplyKeyboardRemove()
            )

        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Операция отменена.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


def main():
    # Создаем папку для презентаций
    os.makedirs(Config.PRESENTATIONS_DIR, exist_ok=True)

    bot = PresentationBot()
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Conversation handler для генерации презентаций
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('generate', bot.generate)],
        states={
            TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_topic)],
            SLIDES: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_slides)],
            ADDITIONAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_additional)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.confirm_generation)],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)]
    )

    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(conv_handler)

    # Запуск бота
    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()