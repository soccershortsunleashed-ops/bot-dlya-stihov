import httpx
from typing import List
from app.infra.ai.base import AudioProvider
from app.infra.config.settings import settings

class SpeechKitProvider(AudioProvider):
    provider_key: str = "speechkit"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or (settings.SPEECHKIT_API_KEY.get_secret_value() if settings.SPEECHKIT_API_KEY else None)
        self.folder_id = settings.YANDEX_CATALOG_ID
        self.url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"

    async def list_models(self) -> List[str]:
        """
        Возвращает список доступных голосов Yandex SpeechKit.
        Документация: https://yandex.cloud/ru/docs/speechkit/tts/voices
        """
        return [
            "filipp", "alena", "madirus", "omazh", "zahar", "ermil", 
            "jane", "oksana", "aleksandr", "kirill", "anton", "marina"
        ]

    async def synthesize(self, text: str, params: dict) -> bytes:
        if not self.api_key:
            raise ValueError("SpeechKit API key is not configured")

        # Параметры синтеза
        data = {
            "text": text,
            "lang": params.get("lang", "ru-RU"),
            "voice": params.get("model", "filipp"), # В нашей системе 'model' в конфиге это голос
            "folderId": self.folder_id,
            "format": "mp3"
        }

        headers = {
            "Authorization": f"Api-Key {self.api_key}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, data=data, headers=headers, timeout=30.0)
            if response.status_code != 200:
                error_detail = response.text
                raise httpx.HTTPStatusError(
                    f"SpeechKit error {response.status_code}: {error_detail}",
                    request=response.request,
                    response=response
                )
            return response.content