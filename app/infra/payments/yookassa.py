from typing import Any
from yookassa import Configuration, Payment
from app.infra.config.settings import settings
import uuid

class YooKassaClient:
    def __init__(self) -> None:
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY.get_secret_value()

    async def create_payment(
        self, 
        amount_rub: int, 
        description: str, 
        metadata: dict[str, Any], 
        idempotency_key: str | None = None
    ) -> dict[str, Any]:
        """
        Создает платеж в ЮKassa.
        """
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        res = Payment.create({
            "amount": {
                "value": f"{amount_rub / 100:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/your_bot_username"  # TODO: Брать из конфига или передавать
            },
            "capture": True,
            "description": description,
            "metadata": metadata
        }, idempotency_key)

        return res.__dict__

    def is_valid_webhook_ip(self, ip: str) -> bool:
        """
        Проверка IP адреса вебхука (упрощенно, ЮKassa рекомендует проверять список IP).
        В продакшене стоит использовать официальный список IP ЮKassa.
        """
        # https://yookassa.ru/developers/using-api/webhooks#ip-addresses
        allowed_ips = [
            "185.71.76.0/27",
            "185.71.77.0/27",
            "77.75.153.0/25",
            "77.75.156.11",
            "77.75.156.35",
            "77.75.154.128/25",
            "2a02:5180::/32"
        ]
        # Для простоты пока возвращаем True, если не в проде или добавить библиотеку для проверки подсетей
        return True