from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import Order
from app.infra.db.repositories.base import BaseRepo


from sqlalchemy import select
from sqlalchemy.orm import selectinload

class OrderRepo(BaseRepo[Order]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Order)

    async def get_user_orders(self, user_id: int) -> list[Order]:
        """Получить все заказы пользователя с загрузкой этапов и артефактов."""
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .options(
                selectinload(Order.stages),
                selectinload(Order.artifacts)
            )
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_order_with_artifacts(self, order_id: UUID) -> Optional[Order]:
        """Получить заказ по ID с загрузкой артефактов."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.artifacts)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()