from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.db.session import async_session_factory
from app.infra.db.repositories.payment_repo import PaymentRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.infra.db.repositories.order_repo import OrderRepo
from app.application.use_cases.handle_yookassa_webhook import HandleYookassaWebhookUseCase

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

async def get_handle_webhook_use_case(session: AsyncSession) -> HandleYookassaWebhookUseCase:
    payment_repo = PaymentRepo(session)
    stage_repo = StageRepo(session)
    order_repo = OrderRepo(session)
    return HandleYookassaWebhookUseCase(payment_repo, stage_repo, order_repo)