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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
TOPIC, SLIDES_COUNT = range(2)


class PresentationBot:
    def __init__(self):
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        self.generator = PresentationGenerator(Config.MISTRAL_API_KEY)
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд"""

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_topic)],
                SLIDES_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_slides_count)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("demo", self.demo_command))
        self.application.add_handler(CommandHandler("status", self.status_command))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало создания презентации"""
        user = update.message.from_user
        logger.info(f"Пользователь {user.first_name} начал создание презентации")

        await update.message.reply_text(
            "🎉 Добро пожаловать в Presentation AI Assistant с Mistral AI!\n\n"
            "Я помогу вам создать профессиональную презентацию.\n"
            "📝 Пожалуйста, введите тему презентации:",
            reply_markup=ReplyKeyboardRemove()
        )

        return TOPIC

    async def get_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получение темы презентации"""
        topic = update.message.text
        context.user_data['topic'] = topic

        # Быстрые варианты количества слайдов
        quick_options = [['5', '8', '10'], ['12', '15']]

        await update.message.reply_text(
            f"📋 Тема: {topic}\n\n"
            f"📊 Сколько слайдов вам нужно? (максимум {Config.MAX_SLIDES})\n"
            f"Или нажмите /default для {Config.DEFAULT_SLIDES} слайдов",
            reply_markup=ReplyKeyboardMarkup(quick_options, one_time_keyboard=True)
        )

        return SLIDES_COUNT

    async def get_slides_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Получение количества слайдов и генерация презентации"""
        user_input = update.message.text
        topic = context.user_data['topic']

        try:
            if user_input == '/default':
                slides_count = Config.DEFAULT_SLIDES
            else:
                slides_count = int(user_input)
                if slides_count > Config.MAX_SLIDES:
                    await update.message.reply_text(
                        f"❌ Максимальное количество слайдов: {Config.MAX_SLIDES}\n"
                        f"Пожалуйста, введите число до {Config.MAX_SLIDES}:"
                    )
                    return SLIDES_COUNT
                if slides_count < 1:
                    await update.message.reply_text("❌ Количество слайдов должно быть больше 0")
                    return SLIDES_COUNT

        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите корректное число:")
            return SLIDES_COUNT

        # Уведомление о начале генерации
        generating_msg = await update.message.reply_text(
            f"🔄 Генерирую презентацию '{topic}'...\n"
            f"📊 Слайдов: {slides_count}\n"
            f"⏳ Это займет 10-30 секунд..."
        )

        try:
            # Генерация презентации
            filename = f"presentation_{update.message.chat_id}.pptx"
            await self.generator.create_presentation(topic, slides_count, filename)

            # Отправка файла
            with open(filename, 'rb') as file:
                await update.message.reply_document(
                    document=file,
                    filename=f"Презентация_{topic.replace(' ', '_')}.pptx",
                    caption=f"✅ Ваша презентация готова!\n\n"
                            f"📖 Тема: {topic}\n"
                            f"📊 Слайдов: {slides_count}\n"
                            f"🤖 Сгенерировано с помощью {Config.MODEL_NAME}\n\n"
                            f"Для создания новой презентации используйте /start"
                )

            # Удаление временного файла
            os.remove(filename)

        except Exception as e:
            logger.error(f"Ошибка генерации: {str(e)}")

            # Попытка создать простую презентацию как запасной вариант
            try:
                await update.message.reply_text("🔄 Пробую альтернативный метод генерации...")
                filename = f"presentation_simple_{update.message.chat_id}.pptx"
                await self.generator.create_simple_presentation(topic, slides_count, filename)

                with open(filename, 'rb') as file:
                    await update.message.reply_document(
                        document=file,
                        filename=f"Презентация_{topic.replace(' ', '_')}_simple.pptx",
                        caption=f"✅ Презентация создана (упрощенный вариант)!\n\n"
                                f"📖 Тема: {topic}\n"
                                f"📊 Слайдов: {slides_count}\n\n"
                                f"Для новой попытки используйте /start"
                    )

                os.remove(filename)

            except Exception as e2:
                await update.message.reply_text(
                    "❌ Произошла ошибка при генерации презентации. "
                    "Пожалуйста, попробуйте позже или измените параметры.\n"
                    f"Ошибка: {str(e2)}"
                )

        # Удаление сообщения о генерации
        try:
            await generating_msg.delete()
        except:
            pass

        return ConversationHandler.END

    async def demo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Демонстрационная команда"""
        await update.message.reply_text(
            "🎯 Демо-режим: создаю презентацию на тему 'Искусственный интеллект в бизнесе'..."
        )

        filename = f"demo_{update.message.chat_id}.pptx"
        try:
            await self.generator.create_presentation(
                "Искусственный интеллект в бизнесе", 6, filename
            )

            with open(filename, 'rb') as file:
                await update.message.reply_document(
                    document=file,
                    filename="Демо_презентация_ИИ_в_бизнесе.pptx",
                    caption="✅ Демо-презентация готова!\n\n"
                            "Попробуйте создать свою с помощью /start"
                )

            os.remove(filename)

        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка демо-генерации: {str(e)}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Проверка статуса бота"""
        status_text = (
            "🤖 **Статус бота**\n\n"
            f"✅ Бот активен\n"
            f"🧠 Модель: {Config.MODEL_NAME}\n"
            f"📊 Макс. слайдов: {Config.MAX_SLIDES}\n"
            f"⚡ API ключ: {'✅ Настроен' if Config.MISTRAL_API_KEY else '❌ Отсутствует'}\n\n"
            "Используйте /start для создания презентации"
        )
        await update.message.reply_text(status_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Справка по боту"""
        help_text = f"""
        🤖 Presentation AI Assistant ({Config.MODEL_NAME})

        Команды:
        /start - Начать создание новой презентации
        /demo - Получить демо-презентацию
        /status - Проверить статус бота
        /help - Показать эту справку

        Как использовать:
        1. Нажмите /start
        2. Введите тему презентации
        3. Укажите количество слайдов (1-{Config.MAX_SLIDES})
        4. Получите готовую презентацию!

        Особенности:
        • Генерация интеллектуального контента через Mistral AI
        • Профессиональное оформление слайдов
        • Автоматическая структуризация
        • Резервные методы генерации

        Примеры тем:
        • Цифровая трансформация бизнеса
        • Маркетинговая стратегия на 2024
        • Внедрение новых технологий
        • Образовательные программы
        """
        await update.message.reply_text(help_text)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена создания презентации"""
        await update.message.reply_text(
            '❌ Создание презентации отменено.',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    def run(self):
        """Запуск бота"""
        print("🤖 Бот запущен с Mistral AI!")
        print(f"📊 Максимум слайдов: {Config.MAX_SLIDES}")
        print(f"🧠 Модель: {Config.MODEL_NAME}")
        self.application.run_polling()


if __name__ == '__main__':
    bot = PresentationBot()
    bot.run()