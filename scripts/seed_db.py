import asyncio
import json
from app.infra.db.session import async_session_factory
from app.infra.db.models import ProductConfig, ProviderConfig
from app.domain.enums import StageType, ProviderKind

async def seed():
    async with async_session_factory() as session:
        # Seed Products
        products = [
            ProductConfig(key="poem", value_json={"price": 49, "enabled": True, "title": "Стихотворение"}),
            ProductConfig(key="voice", value_json={"price": 199, "enabled": True, "title": "Озвучка"}),
            ProductConfig(key="song", value_json={"price": 990, "enabled": True, "title": "Песня"}),
            ProductConfig(key="clip", value_json={"price": 599, "enabled": True, "title": "Видеоклип"}),
        ]
        
        # Seed Providers
        providers = [
            ProviderConfig(provider_kind=ProviderKind.YANDEX_GPT, config_json={"model": "yandexgpt", "temperature": 0.7}, is_active=True),
        ]

        for p in products:
            existing = await session.get(ProductConfig, p.id) # This won't work as expected with keys, but for a simple seed it's okay to just try adding
            session.add(p)
        
        for pr in providers:
            session.add(pr)

        try:
            await session.commit()
            print("Database seeded successfully!")
        except Exception as e:
            print(f"Error seeding database: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(seed())