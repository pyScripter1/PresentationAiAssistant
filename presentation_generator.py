import requests
import json
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from datetime import datetime
from config import Config


class PresentationGenerator:
    def __init__(self):
        self.api_key = Config.MISTRAL_API_KEY
        self.presentations_dir = Config.PRESENTATIONS_DIR

        # Создаем папку для презентаций, если она не существует
        os.makedirs(self.presentations_dir, exist_ok=True)

    def query_mistral_api(self, prompt, model="mistral-small-latest"):
        """
        Отправляет запрос к Mistral AI API и возвращает ответ.
        """
        url = "https://api.mistral.ai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к API: {e}")
            return None
        except KeyError as e:
            print(f"Неожиданный формат ответа от API: {e}")
            return None

    def create_presentation_prompt(self, topic, num_slides=5, additional_prompt=""):
        """
        Создает промпт для генерации презентации с учетом дополнительных пожеланий.
        """
        prompt = f"""
Ты — опытный спикер и копирайтер. Твоя задача — создать подробную структуру и контент для презентации на тему "{topic}".

Презентация должна состоять из {num_slides} слайдов.
"""

        # Добавляем дополнительные пожелания, если они есть
        if additional_prompt:
            prompt += f"\n\nДОПОЛНИТЕЛЬНЫЕ ПОЖЕЛАНИЯ:\n{additional_prompt}\n"

        prompt += f"""

Верни ответ в формате JSON, который легко распарсить. Структура JSON должна быть следующей:

{{
  "presentation_title": "Название презентации",
  "slides": [
    {{
      "slide_number": 1,
      "slide_type": "title",
      "slide_title": "Заголовок презентации",
      "content": [
        "Подзаголовок или дополнительная информация",
      ]
    }},
    {{
      "slide_number": 2,
      "slide_type": "content",
      "slide_title": "Введение",
      "content": [
        "Текст для введения (5-7) предложенией и ключевые тезисы."
      ]
    }},
    {{
      "slide_number": 3,
      "slide_type": "content",
      "slide_title": "Цели",
      "content": [
        "Цель 1",
        "Цель 2",
        "Цель 3",
        "Цель 4",
        "Цель ..."
      ]
    }},
    {{
      "slide_number": 4,
      "slide_type": "content",
      "slide_title": "Основная часть",
      "content": [
        "Основная часть презентации, небольшой текст"
      ]
    }},
    {{
      "slide_number": 5,
      "slide_type": "content",
      "slide_title": "Детали",
      "content": [
        "Деталь 1",
        "Деталь 2",
        "Деталь 3",
        "Деталь 4",
        "Деталь ..."
      ]
    }},
    {{
      "slide_number": 6,
      "slide_type": "content",
      "slide_title": "Примеры",
      "content": [
        "Несколько примеров, которые явно отражают суть темы",
        "Пример 1",
        "Пример 2",
        "Пример 3",
        "Пример 4",
        "Пример ..."
      ]
    }},
    {{
      "slide_number": 7,
      "slide_type": "conclusion",
      "slide_title": "Выводы",
      "content": [
        "Ключевой вывод 1",
        "Ключевой вывод 2",
        "Ключевой вывод ...",
        "Призыв к действию"
      ]
    }}
  ]
}}

Используй четкие, лаконичные формулировки для пунктов списка.
Содержание должно быть информативным и структурированным.

Тема презентации: {topic}
"""
        return prompt

    def create_pptx_from_data(self, presentation_data, output_filename):
        """
        Создает PowerPoint файл из данных презентации.
        """
        try:
            prs = Presentation()

            # Настройки презентации
            prs.slide_width = Inches(13.333)  # 16:9 формат
            prs.slide_height = Inches(7.5)

            title_slide_layout = prs.slide_layouts[0]
            content_slide_layout = prs.slide_layouts[1]

            for slide_info in presentation_data["slides"]:
                slide_type = slide_info.get("slide_type", "content")
                slide_title = slide_info["slide_title"]
                content = slide_info["content"]

                if slide_type == "title":
                    slide = prs.slides.add_slide(title_slide_layout)

                    title_shape = slide.shapes.title
                    subtitle_shape = slide.placeholders[1]

                    title_shape.text = slide_title
                    title_shape.text_frame.paragraphs[0].font.size = Pt(44)
                    title_shape.text_frame.paragraphs[0].font.bold = True

                    if content:
                        subtitle_shape.text = "\n".join(content)
                        subtitle_shape.text_frame.paragraphs[0].font.size = Pt(24)
                        subtitle_shape.text_frame.paragraphs[0].font.color.rgb = RGBColor(100, 100, 100)

                else:
                    slide = prs.slides.add_slide(content_slide_layout)

                    title_shape = slide.shapes.title
                    content_shape = slide.placeholders[1]

                    title_shape.text = slide_title
                    title_shape.text_frame.paragraphs[0].font.size = Pt(32)
                    title_shape.text_frame.paragraphs[0].font.bold = True

                    text_frame = content_shape.text_frame
                    text_frame.clear()
                    text_frame.word_wrap = True

                    for i, point in enumerate(content):
                        if i == 0:
                            p = text_frame.paragraphs[0]
                        else:
                            p = text_frame.add_paragraph()

                        p.text = f"• {point}"
                        p.font.size = Pt(18)
                        p.font.color.rgb = RGBColor(0, 0, 0)
                        p.space_after = Pt(12)

            prs.save(output_filename)
            return output_filename

        except Exception as e:
            print(f"Ошибка при создании PPTX файла: {e}")
            return None

    def clean_json_response(self, response_text):
        """
        Очищает ответ от модели от лишних символов и извлекает JSON.
        """
        try:
            cleaned_response = response_text.strip()

            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]

            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            presentation_data = json.loads(cleaned_response)
            return presentation_data

        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            print(f"Исходный текст: {response_text}")
            return None

    def generate_presentation(self, topic, num_slides=5, additional_prompt=""):
        """
        Основной метод для генерации презентации.
        Возвращает путь к созданному файлу или None в случае ошибки.
        """
        # Генерируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() else "_" for c in topic)
        output_filename = os.path.join(
            self.presentations_dir,
            f"presentation_{safe_topic}_{timestamp}.pptx"
        )

        print(f"🔄 Генерирую презентацию '{topic}'...")

        # Создаем промпт и получаем ответ от Mistral AI
        prompt = self.create_presentation_prompt(topic, num_slides, additional_prompt)
        response_text = self.query_mistral_api(prompt)

        if not response_text:
            print("❌ Не удалось получить ответ от Mistral AI")
            return None

        print("✅ Получен ответ от ИИ. Создаю файл...")

        presentation_data = self.clean_json_response(response_text)

        if not presentation_data:
            print("❌ Не удалось обработать ответ от ИИ")
            return None

        result_file = self.create_pptx_from_data(presentation_data, output_filename)

        if result_file:
            print(f"🎉 Презентация успешно создана: {result_file}")
            return result_file
        else:
            print("❌ Ошибка при создании PPTX файла")
            return None

    def get_presentation_info(self, presentation_data):
        """
        Возвращает информацию о презентации для отправки пользователю.
        """
        if not presentation_data:
            return None

        info = {
            'title': presentation_data.get('presentation_title', 'Без названия'),
            'slides_count': len(presentation_data.get('slides', [])),
            'structure': []
        }

        for slide in presentation_data.get('slides', []):
            info['structure'].append({
                'number': slide.get('slide_number'),
                'title': slide.get('slide_title'),
                'type': slide.get('slide_type', 'content')
            })

        return info


# Функция для обратной совместимости (если нужно)
def generate_presentation(topic, num_slides=5, additional_prompt=""):
    """
    Упрощенная функция для генерации презентации.
    """
    generator = PresentationGenerator()
    return generator.generate_presentation(topic, num_slides, additional_prompt)


if __name__ == "__main__":
    # Тестовый запуск
    generator = PresentationGenerator()

    print("=== Тест генератора презентаций ===")
    topic = input("Введите тему для теста: ").strip()

    result = generator.generate_presentation(
        topic=topic,
        num_slides=3,
        additional_prompt="сделать кратко и по делу"
    )

    if result:
        print(f"Тест успешен! Файл создан: {result}")
    else:
        print("Тест не удался.")