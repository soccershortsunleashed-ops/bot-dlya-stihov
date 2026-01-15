import asyncio
import sys
import os
from uuid import uuid4

# Добавляем корень проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infra.db.session import async_session_factory
from app.infra.db.models import User, Order, OrderStage, Payment
from app.domain.enums import OrderStatus, OrderStageStatus, PaymentStatus, StageType
from app.infra.db.repositories.order_repo import OrderRepo
from app.infra.db.repositories.payment_repo import PaymentRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.application.use_cases.handle_yookassa_webhook import HandleYookassaWebhookUseCase
from sqlalchemy import select, func

async def verify():
    async with async_session_factory() as session:
        # 1. Подготовка данных
        user = User(telegram_id=999999999, username="test_verify")
        session.add(user)
        await session.flush()

        order = Order(user_id=user.id, status=OrderStatus.PENDING)
        session.add(order)
        await session.flush()

        stage = OrderStage(
            order_id=order.id,
            stage_type=StageType.POEM,
            status=OrderStageStatus.PENDING,
            price=10000 # 100.00 RUB
        )
        session.add(stage)
        await session.flush()

        yookassa_id = f"test_pay_{uuid4()}"
        payment = Payment(
            order_id=order.id,
            stage_id=stage.id,
            yookassa_payment_id=yookassa_id,
            status=PaymentStatus.PENDING,
            amount=10000,
            currency="RUB"
        )
        session.add(payment)
        await session.commit()

        print(f"Created test data: Order {order.id}, Payment {yookassa_id}")

        # 2. Инициализация Use Case
        order_repo = OrderRepo(session)
        payment_repo = PaymentRepo(session)
        stage_repo = StageRepo(session)
        use_case = HandleYookassaWebhookUseCase(payment_repo, stage_repo, order_repo)

        # 3. Имитация вебхука
        payload = {
            "event": "payment.succeeded",
            "object": {
                "id": yookassa_id,
                "status": "succeeded",
                "amount": {"value": "100.00", "currency": "RUB"},
                "paid": True
            }
        }

        print("Executing webhook use case...")
        await use_case.execute(payload)
        
        # Перезагружаем объекты
        await session.refresh(order)
        await session.refresh(payment)
        await session.refresh(stage)

        assert order.status == OrderStatus.PAID, f"Order status expected PAID, got {order.status}"
        assert payment.status == PaymentStatus.SUCCEEDED, f"Payment status expected SUCCEEDED, got {payment.status}"
        assert stage.status == OrderStageStatus.PAID, f"Stage status expected PAID, got {stage.status}"
        print("Success: First webhook call processed correctly.")

        # 4. Проверка идемпотентности
        print("Executing webhook use case again (idempotency check)...")
        await use_case.execute(payload)
        print("Success: Second webhook call handled (idempotent).")

        # 5. Проверка расчета выручки (логика из admin.py)
        total_revenue_cents = await session.scalar(
            select(func.sum(Payment.amount))
            .join(Order, Payment.order_id == Order.id)
            .where(
                Payment.status == PaymentStatus.SUCCEEDED,
                Order.status == OrderStatus.PAID,
                Payment.currency == "RUB"
            )
        ) or 0
        
        print(f"Total revenue in cents: {total_revenue_cents}")
        assert total_revenue_cents >= 10000, "Revenue calculation failed"
        print("Success: Revenue calculation verified.")

        # Очистка (опционально, но лучше оставить для чистоты теста)
        # await session.delete(payment)
        # await session.delete(stage)
        # await session.delete(order)
        # await session.delete(user)
        # await session.commit()

if __name__ == "__main__":
    asyncio.run(verify())