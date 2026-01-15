from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import Artifact
from app.infra.db.repositories.base import BaseRepo


class ArtifactRepo(BaseRepo[Artifact]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Artifact)

    async def get_latest_text_artifact(self, order_id: UUID) -> Optional[Artifact]:
        """
        Возвращает последний текстовый артефакт (стих) для заказа.
        """
        from app.domain.enums import ArtifactType
        stmt = (
            select(Artifact)
            .where(Artifact.order_id == order_id, Artifact.type == ArtifactType.TEXT)
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()