from typing import Protocol, List


class TextProvider(Protocol):
    provider_key: str

    async def list_models(self) -> List[str]:
        """
        Возвращает список доступных моделей.
        """
        ...

    async def generate_poem(self, prompt: str, params: dict) -> str:
        """
        Генерирует стихотворение на основе промпта и параметров.
        """
        ...


class AudioProvider(Protocol):
    provider_key: str

    async def list_models(self) -> List[str]:
        """
        Возвращает список доступных голосов/моделей.
        """
        ...

    async def synthesize(self, text: str, params: dict) -> bytes:
        """
        Синтезирует речь и возвращает аудио-контент в байтах.
        """
        ...