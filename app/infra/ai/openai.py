import httpx
import logging
from typing import List
from app.infra.ai.base import TextProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(TextProvider):
    provider_key = "openai"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1"

    async def list_models(self) -> List[str]:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)
                response.raise_for_status()
                data = response.json()
                models = [m["id"] for m in data["data"] if "gpt" in m["id"]]
                return sorted(models)
        except Exception as e:
            logger.error(f"Error listing OpenAI models: {e}")
            return ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]

    async def generate_poem(self, prompt: str, params: dict) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": params.get("model", "gpt-4o-mini"),
            "messages": [
                {"role": "system", "content": "Ты — поэт."},
                {"role": "user", "content": prompt}
            ],
            "temperature": params.get("temperature", 0.7),
            "max_tokens": params.get("max_tokens", 1000)
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=60.0)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]