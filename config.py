import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Конфигурация приложения"""

    # Telegram Bot Token
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    # Mistral AI API Key - только через переменные окружения
    MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

    # Настройки генерации
    MAX_SLIDES = 15
    DEFAULT_SLIDES = 8
    MODEL_NAME = "mistral-large-latest"

    # Валидация конфигурации
    @classmethod
    def validate(cls):
        """Проверка наличия обязательных переменных"""
        missing_vars = []

        if not cls.BOT_TOKEN:
            missing_vars.append('BOT_TOKEN')

        if not cls.MISTRAL_API_KEY:
            missing_vars.append('MISTRAL_API_KEY')

        if missing_vars:
            raise ValueError(
                f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}\n"
                "Пожалуйста, создайте файл .env с этими переменными."
            )

        print("✅ Конфигурация загружена успешно")
        print(f"🤖 Модель: {cls.MODEL_NAME}")
        print(f"📊 Максимум слайдов: {cls.MAX_SLIDES}")


# Валидация при импорте
try:
    Config.validate()
except ValueError as e:
    print(f"❌ Ошибка конфигурации: {e}")