from uuid import UUID
import structlog
from typing import Any, Dict

from app.domain.enums import PaymentStatus, OrderStageStatus, StageType, OrderStatus
from app.infra.db.repositories.payment_repo import PaymentRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.infra.db.repositories.order_repo import OrderRepo

logger = structlog.get_logger()

class HandleYookassaWebhookUseCase:
    def __init__(
        self,
        payment_repo: PaymentRepo,
        stage_repo: StageRepo,
        order_repo: OrderRepo,
    ):
        self.payment_repo = payment_repo
        self.stage_repo = stage_repo
        self.order_repo = order_repo

    async def execute(self, payload: Dict[str, Any]) -> None:
        """
        Обрабатывает входящий вебхук от ЮKassa.
        """
        event = payload.get("event")
        payment_data = payload.get("object", {})
        yookassa_id = payment_data.get("id")

        if not yookassa_id:
            logger.error("webhook_missing_payment_id", payload=payload)
            return

        if event == "payment.succeeded":
            await self._handle_success(payment_data)
        elif event == "payment.canceled":
            await self._handle_canceled(yookassa_id)
        else:
            logger.info("webhook_unhandled_event", event=event, yookassa_id=yookassa_id)

    async def _handle_success(self, payment_data: Dict[str, Any]) -> None:
        yookassa_id = payment_data.get("id")
        
        # Проверка валюты
        amount_data = payment_data.get("amount", {})
        currency = amount_data.get("currency")
        if currency != "RUB":
            logger.error("invalid_currency", yookassa_id=yookassa_id, currency=currency)
            return

        # 1. Находим платеж в нашей БД по yookassa_id
        payment = await self.payment_repo.get_by_yookassa_id(yookassa_id)

        if not payment:
            logger.error("payment_not_found_for_webhook", yookassa_id=yookassa_id)
            return

        if payment.status == PaymentStatus.SUCCEEDED:
            logger.info("payment_already_processed", yookassa_id=yookassa_id)
            return

        # 2. Обновляем статус платежа
        payment.status = PaymentStatus.SUCCEEDED
        
        # 3. Обновляем статус заказа
        order = await self.order_repo.get_by_id(payment.order_id)
        if order:
            order.status = OrderStatus.PAID
            logger.info("order_marked_as_paid", order_id=order.id)

        # 4. Обновляем статус этапа
        stage = await self.stage_repo.get_by_id(payment.stage_id)
        if stage:
            stage.status = OrderStageStatus.PAID
            logger.info("stage_marked_as_paid", stage_id=stage.id, order_id=stage.order_id)
            
            # Постановка задачи в Celery для генерации
            if stage.stage_type == StageType.POEM:
                from app.infra.queue.tasks import generate_poem_task
                generate_poem_task.delay(str(stage.id))
                logger.info("generation_task_enqueued", stage_id=stage.id, stage_type=stage.stage_type)
        
        await self.payment_repo.session.commit()
        logger.info("payment_success_handled", yookassa_id=yookassa_id)

    async def _handle_canceled(self, yookassa_id: str) -> None:
        payment = await self.payment_repo.get_by_yookassa_id(yookassa_id)

        if payment:
            payment.status = PaymentStatus.CANCELED
            await self.payment_repo.session.commit()
            logger.info("payment_canceled_handled", yookassa_id=yookassa_id)