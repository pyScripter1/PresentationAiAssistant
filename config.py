import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # Настройки путей
    PRESENTATIONS_DIR = "presentations"

    # Настройки бота
    MAX_SLIDES = 25
    DEFAULT_SLIDES = 8  # Оптимально для образовательного шаблона