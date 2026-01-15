from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import Payment
from app.infra.db.repositories.base import BaseRepo


class PaymentRepo(BaseRepo[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Payment)

    async def get_by_yookassa_id(self, yookassa_payment_id: str) -> Optional[Payment]:
        """Найти платеж по ID ЮKassa."""
        stmt = select(Payment).where(Payment.yookassa_payment_id == yookassa_payment_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()