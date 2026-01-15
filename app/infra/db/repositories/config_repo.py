from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import ProviderConfig, ProductConfig, ContentPolicy
from app.domain.enums import ProviderKind, StageType
from app.infra.utils.crypto import encryption_service


class ConfigRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_provider_config(self, stage_type: StageType) -> Optional[ProviderConfig]:
        result = await self.session.execute(select(ProviderConfig).where(ProviderConfig.stage_type == stage_type))
        return result.scalars().first()

    async def get_all_provider_configs(self) -> List[ProviderConfig]:
        result = await self.session.execute(select(ProviderConfig))
        return list(result.scalars().all())

    def decrypt_api_key(self, encrypted_key: Optional[str]) -> Optional[str]:
        if not encrypted_key:
            return None
        return encryption_service.decrypt(encrypted_key)

    async def get_product_config(self, key: str) -> Optional[ProductConfig]:
        result = await self.session.execute(select(ProductConfig).where(ProductConfig.key == key))
        return result.scalars().first()

    async def get_content_policy(self, policy_type: str) -> Optional[ContentPolicy]:
        result = await self.session.execute(select(ContentPolicy).where(ContentPolicy.policy_type == policy_type))
        return result.scalars().first()