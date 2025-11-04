import os
import logging
import random
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

# Состояния для ConversationHandler
TEMPLATE, TOPIC, SLIDES, DESIGN, ADDITIONAL, CONFIRM = range(6)


class PresentationBot:
    def __init__(self):
        self.generator = PresentationGenerator()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "👋 Привет! Я бот для генерации профессиональных презентаций.\n"
            "Я создам презентацию с дизайном на любую тему!\n\n"
            "Для начала введите команду /generate"
        )

    async def generate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Сбрасываем данные пользователя
        context.user_data.clear()

        # Предлагаем выбрать шаблон
        available_templates = self.generator.get_available_templates()

        keyboard = [[template] for template in available_templates]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

        template_descriptions = {
            "educational": "🎓 Образовательный - для уроков, лекций и учебных материалов",
            "corporate": "💼 Корпоративный - для бизнес-презентаций и отчетов",
            "creative": "🎨 Креативный - для вдохновляющих выступлений и стартапов"
        }

        description_text = "📝 Выберите тип презентации:\n\n"
        for template in available_templates:
            description_text += f"• {template_descriptions.get(template, template)}\n"

        await update.message.reply_text(
            description_text,
            reply_markup=reply_markup
        )
        return TEMPLATE

    async def process_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        template_choice = update.message.text

        available_templates = self.generator.get_available_templates()
        if template_choice in available_templates:
            context.user_data['template_name'] = template_choice

            template_info = {
                "educational": "Отлично! Создадим образовательную презентацию 🎓",
                "corporate": "Отлично! Создадим бизнес-презентацию 💼",
                "creative": "Отлично! Создадим креативную презентацию 🎨"
            }

            await update.message.reply_text(
                f"{template_info.get(template_choice, '✅ Выбран шаблон: ' + template_choice)}\n\n"
                f"🎯 Теперь введите тему для презентации:",
                reply_markup=ReplyKeyboardRemove()
            )
            return TOPIC
        else:
            await update.message.reply_text(
                "❌ Такого шаблона нет. Выберите из предложенных:",
                reply_markup=ReplyKeyboardMarkup(
                    [[template] for template in available_templates],
                    one_time_keyboard=True
                )
            )
            return TEMPLATE

    async def get_topic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        topic = update.message.text
        if not topic.strip():
            await update.message.reply_text("❌ Тема не может быть пустой. Введите тему:")
            return TOPIC

        context.user_data['topic'] = topic.strip()

        template_name = context.user_data['template_name']
        slide_recommendations = {
            "educational": "8 слайдов (оптимально для урока)",
            "corporate": "10 слайдов (стандарт для бизнес-презентации)",
            "creative": "10 слайдов (идеально для выступления)"
        }

        await update.message.reply_text(
            f"📊 Тема: {topic}\n\n"
            f"Сколько слайдов должно быть в презентации? (от 3 до {Config.MAX_SLIDES}):\n"
            f"Рекомендуется: {slide_recommendations.get(template_name, '8 слайдов')}"
        )
        return SLIDES

    async def get_slides(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            num_slides = int(update.message.text)
            if num_slides < 3:
                await update.message.reply_text(
                    f"⚠️ Минимальное количество слайдов: 3. Установлено значение 3."
                )
                num_slides = 3
            elif num_slides > Config.MAX_SLIDES:
                await update.message.reply_text(
                    f"⚠️ Максимальное количество слайдов: {Config.MAX_SLIDES}. "
                    f"Установлено значение {Config.MAX_SLIDES}."
                )
                num_slides = Config.MAX_SLIDES
        except ValueError:
            # Если введено не число, используем значение по умолчанию для шаблона
            default_slides = {
                "educational": 8,
                "corporate": 10,
                "creative": 10
            }
            template_name = context.user_data['template_name']
            num_slides = default_slides.get(template_name, Config.DEFAULT_SLIDES)
            await update.message.reply_text(
                f"⚠️ Установлено значение по умолчанию: {num_slides} слайдов"
            )

        context.user_data['num_slides'] = num_slides

        # Предлагаем выбрать дизайн
        available_themes = self.generator.get_available_themes()

        if available_themes:
            keyboard = [[theme] for theme in available_themes] + [['🎨 Случайный дизайн']]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

            theme_descriptions = {
                "modern_blue": "🔵 Современный синий - профессионально и строго",
                "elegant_green": "🟢 Элегантный зеленый - свежо и креативно"
            }

            description_text = "🎨 Выберите дизайн презентации:\n\n"
            for theme in available_themes:
                description_text += f"• {theme_descriptions.get(theme, theme)}\n"
            description_text += "\n• 🎨 Случайный дизайн - доверьте выбор нам"

            await update.message.reply_text(
                description_text,
                reply_markup=reply_markup
            )
            return DESIGN
        else:
            # Если нет тем, переходим к дополнениям
            context.user_data['design_theme'] = 'modern_blue'
            await update.message.reply_text(
                "💡 Есть ли дополнительные пожелания к презентации?\n"
                "(например: 'больше примеров', 'акцент на данных', 'минимум текста')\n\n"
                "Или напишите 'нет', если дополнений нет:",
                reply_markup=ReplyKeyboardRemove()
            )
            return ADDITIONAL

    async def get_design(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        design_choice = update.message.text

        if design_choice == '🎨 Случайный дизайн':
            available_themes = self.generator.get_available_themes()
            design_theme = random.choice(available_themes) if available_themes else 'modern_blue'
            context.user_data['design_theme'] = design_theme
            await update.message.reply_text(
                f"🎲 Выбран случайный дизайн: {design_theme}",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            # Проверяем, что выбранная тема существует
            available_themes = self.generator.get_available_themes()
            if design_choice in available_themes:
                context.user_data['design_theme'] = design_choice
                await update.message.reply_text(
                    f"✅ Выбран дизайн: {design_choice}",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await update.message.reply_text(
                    "❌ Такой темы дизайна нет. Выберите из предложенных:",
                    reply_markup=ReplyKeyboardMarkup(
                        [[theme] for theme in available_themes] + [['🎨 Случайный дизайн']],
                        one_time_keyboard=True
                    )
                )
                return DESIGN

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
        template_name = context.user_data['template_name']
        design_theme = context.user_data.get('design_theme', 'modern_blue')
        additional_text = context.user_data['additional']

        template_names = {
            "educational": "🎓 Образовательный",
            "corporate": "💼 Корпоративный",
            "creative": "🎨 Креативный"
        }

        confirmation_text = (
            f"✅ Подтвердите создание презентации:\n\n"
            f"🎯 Тема: {topic}\n"
            f"📊 Слайдов: {num_slides}\n"
            f"📝 Шаблон: {template_names.get(template_name, template_name)}\n"
            f"🎨 Дизайн: {design_theme}\n"
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
                "🔄 Генерирую презентацию... Это может занять 1-2 минуты.",
                reply_markup=ReplyKeyboardRemove()
            )

            try:
                # Генерация презентации
                topic = context.user_data['topic']
                num_slides = context.user_data['num_slides']
                template_name = context.user_data['template_name']
                design_theme = context.user_data.get('design_theme', 'modern_blue')
                additional = context.user_data['additional']

                # Добавляем информацию о количестве слайдов в дополнения
                if additional:
                    full_additional = f"{additional}. Количество слайдов: {num_slides}"
                else:
                    full_additional = f"Количество слайдов: {num_slides}"

                logger.info(
                    f"Генерация презентации: тема='{topic}', шаблон='{template_name}', дизайн='{design_theme}', слайдов={num_slides}")

                file_path = self.generator.generate_presentation(
                    topic=topic,
                    template_name=template_name,
                    additional_prompt=full_additional,
                    design_theme=design_theme
                )

                if file_path and os.path.exists(file_path):
                    # Отправка файла пользователю
                    with open(file_path, 'rb') as file:
                        template_emojis = {
                            "educational": "🎓",
                            "corporate": "💼",
                            "creative": "🎨"
                        }

                        caption = (
                            f"{template_emojis.get(template_name, '🎉')} Ваша презентация готова!\n"
                            f"🎯 Тема: {topic}\n"
                            f"📊 Слайдов: {num_slides}\n"
                            f"📝 Тип: {template_name}\n"
                            f"🎨 Дизайн: {design_theme}"
                        )

                        await update.message.reply_document(
                            document=file,
                            filename=os.path.basename(file_path),
                            caption=caption
                        )
                    # Удаляем временный файл
                    os.remove(file_path)
                    logger.info(f"Презентация успешно отправлена и удалена: {file_path}")
                else:
                    await update.message.reply_text(
                        "❌ Произошла ошибка при генерации презентации. "
                        "Попробуйте изменить тему или упростить запрос."
                    )
                    logger.error("Файл презентации не был создан")

            except Exception as e:
                logger.error(f"Error generating presentation: {e}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при генерации. "
                    "Попробуйте позже или измените параметры запроса."
                )

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

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "📚 Доступные команды:\n\n"
            "/start - Начать работу с ботом\n"
            "/generate - Создать новую презентацию\n"
            "/templates - Показать доступные шаблоны\n"
            "/themes - Показать доступные темы дизайна\n"
            "/help - Показать эту справку\n\n"
            "🎨 Бот создает презентации с:\n"
            "• Профессиональным дизайном\n"
            "• Разными типами контента\n"
            "• Автоматическим форматированием\n"
            "• Выбором шаблонов под разные задачи"
        )
        await update.message.reply_text(help_text)

    async def show_themes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает доступные темы дизайна"""
        available_themes = self.generator.get_available_themes()

        if available_themes:
            themes_text = "🎨 Доступные темы дизайна:\n\n"
            theme_descriptions = {
                "modern_blue": "🔵 Современный синий - профессиональный стиль",
                "elegant_green": "🟢 Элегантный зеленый - свежий и креативный"
            }

            for theme in available_themes:
                themes_text += f"• {theme} - {theme_descriptions.get(theme, 'Профессиональный дизайн')}\n"

            themes_text += "\n🎲 Или выберите 'Случайный дизайн' при создании презентации!"
        else:
            themes_text = "❌ Темы дизайна не найдены. Используется стандартный дизайн."

        await update.message.reply_text(themes_text)

    async def show_templates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает доступные шаблоны презентаций"""
        available_templates = self.generator.get_available_templates()

        if available_templates:
            templates_text = "📝 Доступные шаблоны презентаций:\n\n"

            template_descriptions = {
                "educational": (
                    "🎓 Образовательный шаблон\n"
                    "• Для уроков, лекций, учебных материалов\n"
                    "• Структура: цели → теория → примеры → задания → выводы\n"
                    "• Идеально для учителей и студентов"
                ),
                "corporate": (
                    "💼 Корпоративный шаблон\n"
                    "• Для бизнес-презентаций, отчетов, проектов\n"
                    "• Структура: повестка → проблема → решение → метрики → план\n"
                    "• Подходит для встреч с инвесторами и руководством"
                ),
                "creative": (
                    "🎨 Креативный шаблон\n"
                    "• Для вдохновляющих выступлений, стартапов\n"
                    "• Структура: история → идея → факты → призыв к действию\n"
                    "• Идеально для TED-формата и мотивационных выступлений"
                )
            }

            for template in available_templates:
                templates_text += f"{template_descriptions.get(template, template)}\n\n"

            templates_text += "Используйте /generate чтобы создать презентацию!"
        else:
            templates_text = "❌ Шаблоны не найдены."

        await update.message.reply_text(templates_text)


def main():
    # Создаем папку для презентаций
    os.makedirs(Config.PRESENTATIONS_DIR, exist_ok=True)

    bot = PresentationBot()
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Conversation handler для генерации презентаций
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('generate', bot.generate)],
        states={
            TEMPLATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.process_template)],
            TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_topic)],
            SLIDES: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_slides)],
            DESIGN: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_design)],
            ADDITIONAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_additional)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.confirm_generation)],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)]
    )

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("themes", bot.show_themes))
    application.add_handler(CommandHandler("templates", bot.show_templates))
    application.add_handler(conv_handler)

    # Запуск бота
    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()