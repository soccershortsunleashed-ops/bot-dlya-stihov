import asyncio
from sqlalchemy import select
from app.infra.db.session import async_session_factory
from app.infra.db.models import ProviderConfig
from app.domain.enums import ProviderKind

async def update():
    async with async_session_factory() as session:
        # Use string "gemini" because ProviderKind.GEMINI might not match the DB value exactly if enum handling is tricky
        result = await session.execute(select(ProviderConfig).where(ProviderConfig.provider_kind == "gemini"))
        config = result.scalars().first()
        
        if not config:
             # Try with uppercase
             result = await session.execute(select(ProviderConfig).where(ProviderConfig.provider_kind == "GEMINI"))
             config = result.scalars().first()

        if config:
            print(f"Old config: {config.config_json}")
            new_config = config.config_json.copy()
            # Explicitly set max_tokens to a higher value
            new_config["max_tokens"] = 4096
            # Ensure model params are correct
            new_config["temperature"] = 0.7
            
            config.config_json = new_config
            session.add(config)
            await session.commit()
            print(f"New config: {config.config_json}")
        else:
            print("Gemini config not found!")

if __name__ == "__main__":
    asyncio.run(update())