import logging
from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.texts.ru import START_TEXT
from app.bot.keyboards.common import get_main_menu_keyboard
from app.infra.db.repositories.user_repo import UserRepo
from app.infra.db.models import User

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info(f"Received /start from user {message.from_user.id}")
    try:
        await state.clear()
        logger.debug("State cleared")
        
        user_repo = UserRepo(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)
        logger.debug(f"User found: {user is not None}")
        
        if not user:
            logger.info(f"Creating new user {message.from_user.id}")
            user = await user_repo.create(
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
            logger.info(f"User created: {user.id}")
        
        logger.info(f"Sending start text to {message.from_user.id}")
        await message.answer(
            START_TEXT,
            reply_markup=get_main_menu_keyboard()
        )
        logger.info("Start text sent successfully")
    except Exception as e:
        logger.exception(f"Error in cmd_start: {e}")
        await message.answer("Произошла ошибка при запуске бота. Попробуйте позже.")