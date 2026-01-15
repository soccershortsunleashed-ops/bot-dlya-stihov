import httpx
from typing import List
from app.infra.ai.base import TextProvider
from app.infra.config.settings import settings


class YandexGPTProvider(TextProvider):
    provider_key: str = "yandex_gpt"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or (settings.YANDEX_GPT_API_KEY.get_secret_value() if settings.YANDEX_GPT_API_KEY else None)
        self.folder_id = settings.YANDEX_CATALOG_ID
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    async def list_models(self) -> List[str]:
        # YandexGPT doesn't have a simple public models list API like OpenAI yet,
        # or it's folder-dependent. Returning a static list of known models for now.
        return ["yandexgpt/latest", "yandexgpt-lite/latest", "yandexgpt/rc"]

    async def generate_poem(self, prompt: str, params: dict) -> str:
        if not self.api_key or not self.folder_id:
            raise ValueError("YandexGPT credentials are not configured")

        model_uri = f"gpt://{self.folder_id}/{params.get('model', 'yandexgpt/latest')}"
        
        payload = {
            "modelUri": model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": params.get("temperature", 0.6),
                "maxTokens": params.get("max_tokens", 1000)
            },
            "messages": [
                {
                    "role": "system",
                    "text": params.get("system_prompt", "Ты — профессиональный поэт. Пиши смешные, но добрые стихи.")
                },
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            
            return result["result"]["alternatives"][0]["message"]["text"]