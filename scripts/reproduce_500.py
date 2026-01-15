import asyncio
import logging
import sys
import os

# Add current directory to path for imports
sys.path.append(os.getcwd())

from sqlalchemy import select
from app.infra.db.session import async_session_factory
from app.infra.db.models import ProviderConfig
from app.domain.enums import StageType, ProviderKind
from app.web.routes.admin import update_provider
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reproduce():
    async with async_session_factory() as session:
        # Create a mock request
        request = MagicMock()
        request.headers = {}
        
        print("\n--- Testing update_provider with YANDEX_GPT ---")
        try:
            # Try to update POEM provider to YANDEX_GPT
            # This should trigger the code path that might fail
            response = await update_provider(
                request=request,
                stage_type=StageType.POEM,
                kind=ProviderKind.YANDEX_GPT,
                api_key="test_key",
                model="yandexgpt/latest",
                admin="admin",
                session=session
            )
            print(f"Response: {response}")
        except Exception as e:
            print(f"CAUGHT ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(reproduce())