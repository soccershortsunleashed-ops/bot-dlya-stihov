from uuid import UUID
from typing import Dict, Any

from app.domain.enums import PaymentStatus
from app.infra.db.models import Payment
from app.infra.db.repositories.payment_repo import PaymentRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.infra.payments.yookassa import YooKassaClient

class StartPaymentUseCase:
    def __init__(
        self,
        payment_repo: PaymentRepo,
        stage_repo: StageRepo,
        yookassa_client: YooKassaClient,
    ):
        self.payment_repo = payment_repo
        self.stage_repo = stage_repo
        self.yookassa_client = yookassa_client

    async def execute(self, stage_id: UUID) -> Dict[str, Any]:
        """
        Инициирует процесс оплаты для конкретного этапа заказа.
        """
        stage = await self.stage_repo.get_by_id(stage_id)
        if not stage:
            raise ValueError(f"Stage {stage_id} not found")

        # 1. Создаем платеж в ЮKassa
        description = f"Оплата этапа {stage.stage_type} для заказа {stage.order_id}"
        metadata = {
            "order_id": str(stage.order_id),
            "stage_id": str(stage.id),
            "stage_type": stage.stage_type
        }
        
        # Используем stage_id как часть ключа идемпотентности для простоты
        idempotency_key = f"pay_{stage.id}"
        
        yoo_payment = await self.yookassa_client.create_payment(
            amount_rub=stage.price,
            description=description,
            metadata=metadata,
            idempotency_key=idempotency_key
        )

        # 2. Сохраняем информацию о платеже в БД
        # Извлекаем ID платежа из ответа (объект Payment из библиотеки yookassa имеет поле id)
        # Так как мы вернули __dict__, ищем там
        yoo_id = yoo_payment.get('id') or yoo_payment.get('_id')
        
        db_payment = Payment(
            order_id=stage.order_id,
            stage_id=stage.id,
            yookassa_payment_id=yoo_id,
            status=PaymentStatus.PENDING,
            amount=stage.price
        )
        
        await self.payment_repo.add(db_payment)
        
        # 3. Возвращаем данные для подтверждения (ссылку на оплату)
        # В объекте ЮKassa это confirmation['confirmation_url']
        confirmation = yoo_payment.get('confirmation', {})
        return {
            "payment_id": db_payment.id,
            "yookassa_id": yoo_id,
            "confirmation_url": confirmation.get('confirmation_url')
        }