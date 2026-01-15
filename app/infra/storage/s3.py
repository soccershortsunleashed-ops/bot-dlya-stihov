import aiobotocore.session
from app.infra.config.settings import settings
from typing import Optional

class S3Storage:
    def __init__(self):
        self.session = aiobotocore.session.get_session()
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.bucket_name = settings.S3_BUCKET_NAME
        self.access_key = settings.S3_ACCESS_KEY.get_secret_value() if settings.S3_ACCESS_KEY else None
        self.secret_key = settings.S3_SECRET_KEY.get_secret_value() if settings.S3_SECRET_KEY else None

    async def upload_file(self, content: bytes, key: str, content_type: str = "audio/mpeg") -> Optional[str]:
        """
        Загружает файл в S3 и возвращает ключ (путь).
        """
        if not all([self.access_key, self.secret_key, self.bucket_name]):
            return None

        async with self.session.create_client(
            's3',
            region_name='ru-central1',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        ) as client:
            await client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type
            )
            return key

    def get_url(self, key: str) -> str:
        """
        Возвращает публичную ссылку на файл (если бакет публичный).
        """
        return f"{self.endpoint_url}/{self.bucket_name}/{key}"