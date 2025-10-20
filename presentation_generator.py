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
        self.templates_dir = "templates"

        # Создаем папки, если они не существуют
        os.makedirs(self.presentations_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)

        # Загружаем доступные шаблоны
        self.available_templates = self._load_available_templates()

    def _load_available_templates(self):
        """Загружает список доступных шаблонов"""
        templates = {}
        if os.path.exists(self.templates_dir):
            for file in os.listdir(self.templates_dir):
                if file.endswith('.json'):
                    template_name = file.replace('.json', '')
                    try:
                        with open(os.path.join(self.templates_dir, file), 'r', encoding='utf-8') as f:
                            templates[template_name] = json.load(f)
                    except Exception as e:
                        print(f"Ошибка загрузки шаблона {file}: {e}")
        return templates

    def get_available_templates(self):
        """Возвращает список доступных шаблонов"""
        return list(self.available_templates.keys())

    def load_template(self, template_name):
        """Загружает конкретный шаблон"""
        return self.available_templates.get(template_name)

    def query_mistral_api(self, prompt, model="mistral-small-latest"):
        """Отправляет запрос к Mistral AI API и возвращает ответ."""
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

    def create_presentation_prompt(self, topic, template_name="educational", additional_prompt=""):
        """Создает промпт для генерации презентации по шаблону."""

        template = self.load_template(template_name)
        if not template:
            raise ValueError(f"Шаблон '{template_name}' не найден")

        prompt = f"""
Ты — опытный преподаватель и создатель образовательных материалов. 
Твоя задача — создать подробную структуру и контент для учебной презентации на тему "{topic}".

ИСПОЛЬЗУЙ СТРОГО СЛЕДУЮЩУЮ СТРУКТУРУ СЛАЙДОВ:
"""

        # Добавляем инструкции для каждого слайда из шаблона
        for slide_template in template["slides_structure"]:
            prompt += f"""
СЛАЙД {slide_template['slide_number']}: {slide_template['slide_title']}
ИНСТРУКЦИЯ: {slide_template['instructions']}
СОДЕРЖАНИЕ: Заполни 3-4 пункта содержания для этого слайда

"""

        # Добавляем дополнительные пожелания
        if additional_prompt:
            prompt += f"\nДОПОЛНИТЕЛЬНЫЕ ПОЖЕЛАНИЯ:\n{additional_prompt}\n"

        prompt += f"""
Верни ответ в формате JSON. Структура JSON должна быть следующей:

{{
  "presentation_title": "Название презентации",
  "template_used": "{template_name}",
  "slides": [
    {{
      "slide_number": 1,
      "slide_type": "title",
      "slide_title": "Название темы",
      "content": [
        "Пункт 1",
        "Пункт 2",
        "Пункт 3"
      ]
    }},
    // ... остальные слайды по структуре шаблона
  ]
}}

ВАЖНЫЕ ТРЕБОВАНИЯ:
- Строго следуй структуре шаблона
- Для каждого слайда создай 3-4 информативных пункта
- Используй образовательный стиль изложения
- Делай содержание практическим и полезным для обучения
- Избегай лишней информации, будь лаконичным

Тема презентации: {topic}
"""
        return prompt

    def create_pptx_from_data(self, presentation_data, output_filename):
        """Создает PowerPoint файл из данных презентации."""
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
                    title_shape.text = slide_title
                    title_shape.text_frame.paragraphs[0].font.size = Pt(44)
                    title_shape.text_frame.paragraphs[0].font.bold = True

                    # Для титульного слайда не показываем подзаголовок (автора)
                    subtitle_shape = slide.placeholders[1]
                    subtitle_shape.text = ""  # Очищаем поле автора

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
        """Очищает ответ от модели от лишних символов и извлекает JSON."""
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

    def generate_presentation(self, topic, template_name="educational", additional_prompt=""):
        """Основной метод для генерации презентации по шаблону."""

        # Генерируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() else "_" for c in topic)
        output_filename = os.path.join(
            self.presentations_dir,
            f"presentation_{safe_topic}_{timestamp}.pptx"
        )

        print(f"🔄 Генерирую презентацию '{topic}' по шаблону '{template_name}'...")

        # Создаем промпт и получаем ответ от Mistral AI
        prompt = self.create_presentation_prompt(topic, template_name, additional_prompt)
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
        """Возвращает информацию о презентации для отправки пользователю."""
        if not presentation_data:
            return None

        info = {
            'title': presentation_data.get('presentation_title', 'Без названия'),
            'template': presentation_data.get('template_used', 'unknown'),
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


# Функция для обратной совместимости
def generate_presentation(topic, template_name="educational", additional_prompt=""):
    generator = PresentationGenerator()
    return generator.generate_presentation(topic, template_name, additional_prompt)


if __name__ == "__main__":
    # Тестовый запуск
    generator = PresentationGenerator()

    print("=== Тест генератора презентаций с шаблонами ===")
    print(f"Доступные шаблоны: {generator.get_available_templates()}")

    topic = input("Введите тему для теста: ").strip()
    template = input("Введите имя шаблона (по умолчанию educational): ").strip() or "educational"

    result = generator.generate_presentation(
        topic=topic,
        template_name=template,
        additional_prompt="сделать практично и с примерами из реальной жизни"
    )

    if result:
        print(f"Тест успешен! Файл создан: {result}")
    else:
        print("Тест не удался.")