import asyncio
from sqlalchemy import select
from app.infra.db.session import async_session_factory
from app.infra.db.models import ProviderConfig
from app.domain.enums import ProviderKind

async def check():
    async with async_session_factory() as session:
        result = await session.execute(select(ProviderConfig))
        configs = result.scalars().all()
        print(f"Found {len(configs)} provider configs")
        for c in configs:
            print(f"Provider: {c.provider_kind}, Active: {c.is_active}, Config: {c.config_json}")

if __name__ == "__main__":
    asyncio.run(check())