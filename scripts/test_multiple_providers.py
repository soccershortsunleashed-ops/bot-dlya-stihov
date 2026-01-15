import asyncio
import logging
import sys
import os

# Add current directory to path for imports
sys.path.append(os.getcwd())

from app.infra.db.session import async_session_factory
from app.infra.db.models import ProviderConfig
from app.domain.enums import StageType, ProviderKind
from app.web.routes.admin import update_provider
from unittest.mock import MagicMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_multiple():
    async with async_session_factory() as session:
        # Create a mock request
        request = MagicMock()
        request.headers = {}
        
        print("\n--- Testing multiple providers with same provider_kind ---")
        try:
            # 1. Update POEM to YANDEX_GPT
            print("Updating POEM to YANDEX_GPT...")
            await update_provider(
                request=request,
                stage_type=StageType.POEM,
                kind=ProviderKind.YANDEX_GPT,
                api_key="test_key_poem",
                model="yandexgpt/latest",
                admin="admin",
                session=session
            )
            
            # 2. Update VOICE to YANDEX_GPT (if allowed by logic, though VOICE usually uses SPEECHKIT)
            # Let's try something that makes sense, like two different StageTypes using the same kind
            # Actually, the requirement is "several configurations with same provider_kind for different stages"
            print("Updating SONG to YANDEX_GPT (test same kind for different stage)...")
            await update_provider(
                request=request,
                stage_type=StageType.SONG,
                kind=ProviderKind.YANDEX_GPT,
                api_key="test_key_song",
                model="yandexgpt/latest",
                admin="admin",
                session=session
            )
            
            print("SUCCESS: Both updates completed without IntegrityError")
            
        except Exception as e:
            print(f"FAILED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_multiple())