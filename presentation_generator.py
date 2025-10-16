from mistralai import Mistral
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
import asyncio
import aiofiles
import os
import json
from typing import List, Dict
from config import Config


class PresentationGenerator:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Mistral API ключ не предоставлен")

        self.client = Mistral(api_key=api_key)
        self.template_path = "templates/template.pptx"
        self.model_name = Config.MODEL_NAME

    async def generate_content(self, topic: str, slides_count: int) -> List[Dict]:
        """Генерация контента для презентации через Mistral AI"""

        prompt = f"""
        Ты эксперт по созданию презентаций. Создай структуру презентации на тему "{topic}" из {slides_count} слайдов.

        Требования:
        - Первый слайд - титульный
        - Последний слайд - заключительный с выводами
        - Остальные слайды - содержательные
        - Каждый слайд должен иметь четкую структуру
        - Используй маркированные списки по 3-5 пунктов

        Верни ответ ТОЛЬКО в формате JSON без каких-либо дополнительных текстов:
        {{
            "slides": [
                {{
                    "title": "Заголовок слайда",
                    "content": ["Пункт 1", "Пункт 2", "Пункт 3"],
                    "slide_type": "title|content|summary"
                }}
            ]
        }}

        slide_type может быть: "title" (титульный), "content" (основной контент), "summary" (заключительный)
        """

        try:
            response = self.client.chat.complete(
                model=self.model_name,
                messages=[
                    {"role": "system",
                     "content": "Ты профессиональный создатель презентаций. Создавай четкие, структурированные и информативные слайды."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            return self._parse_content(content)

        except Exception as e:
            print(f"Ошибка Mistral API: {str(e)}")
            # Fallback: создаем базовую структуру
            return self._create_fallback_content(topic, slides_count)

    def _parse_content(self, content: str) -> List[Dict]:
        """Парсинг сгенерированного контента"""
        try:
            data = json.loads(content)
            slides = data.get("slides", [])

            # Валидация структуры
            for slide in slides:
                if not all(key in slide for key in ['title', 'content', 'slide_type']):
                    raise ValueError("Неверная структура слайда")

            return slides

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Ошибка парсинга JSON: {e}")
            raise Exception("Ошибка обработки ответа от AI")

    def _create_fallback_content(self, topic: str, slides_count: int) -> List[Dict]:
        """Создание резервного контента при ошибке API"""
        slides = []

        # Титульный слайд
        slides.append({
            "title": topic,
            "content": ["Презентация создана автоматически", f"Количество слайдов: {slides_count}"],
            "slide_type": "title"
        })

        # Содержательные слайды
        for i in range(1, slides_count - 1):
            slides.append({
                "title": f"Аспект {i} темы '{topic}'",
                "content": [
                    f"Ключевой момент {i}.1",
                    f"Ключевой момент {i}.2",
                    f"Ключевой момент {i}.3",
                    "Дополнительная информация"
                ],
                "slide_type": "content"
            })

        # Заключительный слайд
        if slides_count > 1:
            slides.append({
                "title": "Заключение",
                "content": [
                    "Основные выводы",
                    "Рекомендации",
                    "Благодарность за внимание"
                ],
                "slide_type": "summary"
            })

        return slides

    async def create_presentation(self, topic: str, slides_count: int, filename: str) -> str:
        """Создание PowerPoint презентации"""

        # Генерация контента
        slides_content = await self.generate_content(topic, slides_count)

        # Ограничение количества слайдов по фактическому контенту
        actual_slides_count = min(len(slides_content), slides_count)
        slides_content = slides_content[:actual_slides_count]

        # Создание презентации
        if os.path.exists(self.template_path):
            prs = Presentation(self.template_path)
            # Очистка шаблонных слайдов
            for i in range(len(prs.slides) - 1, -1, -1):
                rId = prs.slides._sldIdLst[i].rId
                prs.part.related_parts[rId].drop_tree()
            prs.slides._sldIdLst.clear()
        else:
            prs = Presentation()

        # Создание слайдов
        for i, slide_data in enumerate(slides_content):
            if i == 0:
                # Титульный слайд
                slide_layout = prs.slide_layouts[0]
            else:
                # Контентные слайды
                slide_layout = prs.slide_layouts[1]

            slide = prs.slides.add_slide(slide_layout)

            # Заголовок
            title = slide.shapes.title
            if title:
                title.text = slide_data["title"]
                self._format_title(title)

            # Контент для нетитальных слайдов
            if slide_data["slide_type"] != "title" and len(slide.placeholders) > 1:
                content_shape = slide.placeholders[1]
                if content_shape.has_text_frame:
                    text_frame = content_shape.text_frame
                    text_frame.clear()
                    text_frame.word_wrap = True

                    for j, point in enumerate(slide_data["content"]):
                        if j == 0:
                            p = text_frame.paragraphs[0]
                        else:
                            p = text_frame.add_paragraph()

                        p.text = f"• {point}"
                        p.level = 0
                        p.font.size = Pt(20)
                        p.font.name = "Arial"
                        p.font.color.rgb = RGBColor(0, 0, 0)
                        p.space_after = Pt(12)

        # Сохранение
        prs.save(filename)
        return filename

    def _format_title(self, title):
        """Форматирование заголовка"""
        title.text_frame.paragraphs[0].font.size = Pt(32)
        title.text_frame.paragraphs[0].font.bold = True
        title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 0, 139)  # Темно-синий
        title.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        title.text_frame.vertical_anchor = 1  # Middle

    async def create_simple_presentation(self, topic: str, slides_count: int, filename: str) -> str:
        """Альтернативный метод создания презентации"""
        prs = Presentation()

        # Титульный слайд
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]

        title.text = topic
        subtitle.text = f"Автоматически сгенерированная презентация\n{slides_count} слайдов"

        # Контентные слайды
        for i in range(1, slides_count):
            content_slide_layout = prs.slide_layouts[1]
            slide = prs.slides.add_slide(content_slide_layout)

            title = slide.shapes.title
            content = slide.placeholders[1]

            title.text = f"{topic} - Часть {i}"

            if content.has_text_frame:
                tf = content.text_frame
                tf.text = f"Ключевые аспекты части {i}:"
                p = tf.add_paragraph()
                p.text = "• Важный момент 1"
                p = tf.add_paragraph()
                p.text = "• Важный момент 2"
                p = tf.add_paragraph()
                p.text = "• Важный момент 3"

        prs.save(filename)
        return filename