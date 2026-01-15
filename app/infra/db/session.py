from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.infra.config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Using database URL: {settings.FINAL_DATABASE_URL}")

engine = create_async_engine(settings.FINAL_DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)