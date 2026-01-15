from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # Postgres
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432

    DATABASE_URL: str | None = None

    @property
    def FINAL_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Bot
    BOT_TOKEN: SecretStr

    # Yookassa
    YOOKASSA_SHOP_ID: str
    YOOKASSA_SECRET_KEY: SecretStr

    # Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: SecretStr
    ADMIN_SECRET_KEY: SecretStr

    # AI Providers
    YANDEX_GPT_API_KEY: SecretStr | None = None
    YANDEX_CATALOG_ID: str | None = None
    SPEECHKIT_API_KEY: SecretStr | None = None
    SUNO_API_KEY: SecretStr | None = None
    PIKA_API_KEY: SecretStr | None = None
    GEMINI_API_KEY: SecretStr | None = None

    # Object Storage
    S3_ACCESS_KEY: SecretStr | None = None
    S3_SECRET_KEY: SecretStr | None = None
    S3_BUCKET_NAME: str | None = None
    S3_ENDPOINT_URL: str = "https://storage.yandexcloud.net"


settings = Settings()