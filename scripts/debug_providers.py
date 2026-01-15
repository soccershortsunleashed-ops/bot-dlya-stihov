import asyncio
import logging
from sqlalchemy import select
from app.infra.db.session import async_session_factory
from app.infra.db.models import ProviderConfig, APIKey
from app.domain.enums import StageType, ProviderKind

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_db():
    async with async_session_factory() as session:
        print("--- Provider Configs ---")
        res = await session.execute(select(ProviderConfig))
        configs = res.scalars().all()
        print(f"Total configs: {len(configs)}")
        for c in configs:
            print(f"ID: {c.id}, Stage: {c.stage_type}, Kind: {c.provider_kind}, Status: {c.status}")
            print(f"  Model: {c.model}, Cache: {c.models_cache}")
            print(f"  Has Key: {bool(c.api_key_encrypted)}")
        
        print("\n--- API Keys History ---")
        res = await session.execute(select(APIKey))
        keys = res.scalars().all()
        for k in keys:
            print(f"ID: {k.id}, ProviderID: {k.provider_id}, Active: {k.is_active}, Status: {k.status}")

if __name__ == "__main__":
    asyncio.run(debug_db())