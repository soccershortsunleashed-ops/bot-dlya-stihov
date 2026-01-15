import asyncio
import logging
from aiogram import Bot
from app.infra.config.settings import settings
from app.infra.db.session import async_session_factory
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diag")

async def diag():
    logger.info("--- Starting diagnostics ---")
    
    # 1. Check Token
    token = settings.BOT_TOKEN.get_secret_value()
    logger.info(f"Token (first 10 chars): {token[:10]}...")
    bot = Bot(token=token)
    try:
        me = await bot.get_me()
        logger.info(f"Successfully connected to Telegram! Bot: @{me.username} (ID: {me.id})")
        
        webhook_info = await bot.get_webhook_info()
        logger.info(f"Webhook info: {webhook_info}")
        if webhook_info.url:
            logger.warning(f"Webhook is active! Polling will NOT work. URL: {webhook_info.url}")
            logger.info("Deleting webhook...")
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook deleted.")
        else:
            logger.info("No active webhook found. Polling should work.")

    except Exception as e:
        logger.error(f"Failed to connect to Telegram: {e}")
    finally:
        await bot.session.close()

    # 2. Check DB
    logger.info(f"Checking DB connection to: {settings.FINAL_DATABASE_URL}")
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            logger.info(f"DB connection successful: {result.scalar() == 1}")
            
            # Check if users table exists
            from app.infra.db.models import User
            from sqlalchemy import select
            try:
                user_count = await session.execute(text("SELECT count(*) FROM users"))
                logger.info(f"Users table exists. Count: {user_count.scalar()}")
            except Exception as db_e:
                logger.error(f"Error checking users table: {db_e}")
                
    except Exception as e:
        logger.error(f"DB connection failed: {e}")

    logger.info("--- Diagnostics finished ---")

if __name__ == "__main__":
    asyncio.run(diag())