from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import OrderStage
from app.infra.db.repositories.base import BaseRepo


class StageRepo(BaseRepo[OrderStage]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, OrderStage)