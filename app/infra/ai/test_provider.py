from app.infra.ai.base import TextProvider


class DummyTextProvider(TextProvider):
    provider_key: str = "test_text_1"

    async def generate_poem(self, prompt: str, params: dict) -> str:
        return (
            "Розы красные,\n"
            "Фиалки синие,\n"
            "Этот стих тестовый,\n"
            "И вы очень сильные!"
        )