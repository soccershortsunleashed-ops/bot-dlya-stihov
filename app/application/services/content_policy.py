import re
from typing import List


class ContentPolicy:
    def __init__(self, stop_words: List[str] = None):
        self.stop_words = stop_words or []

    def is_appropriate(self, text: str) -> bool:
        """
        Проверяет текст на наличие стоп-слов и других нарушений политики.
        """
        if not text:
            return False

        # Приводим к нижнему регистру для проверки
        text_lower = text.lower()

        for word in self.stop_words:
            if re.search(rf"\b{re.escape(word.lower())}\b", text_lower):
                return False

        return True

    def clean_text(self, text: str) -> str:
        """
        Базовая очистка текста.
        """
        if not text:
            return ""
        return text.strip()