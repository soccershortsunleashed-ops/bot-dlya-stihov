import asyncio
import sys
import logging
from app.bot.main import main

async def run_limited():
    logging.basicConfig(level=logging.INFO)
    try:
        # Запускаем бота с таймаутом 10 секунд
        await asyncio.wait_for(main(), timeout=10)
    except asyncio.TimeoutError:
        print("Bot ran for 10 seconds successfully (timeout reached)")
    except Exception as e:
        print(f"Bot failed during startup or run: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_limited())