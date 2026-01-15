import logging
from uuid import UUID
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.enums import OrderStageStatus
from app.bot.fsm.states import PoemFlow
from app.bot.texts.ru import (
    POEM_OCCASION_TEXT, POEM_RECIPIENT_TEXT, POEM_DETAILS_TEXT,
    CONFIRM_ORDER_TEXT, AWAIT_PAYMENT_TEXT, CANCELLED_TEXT,
    AWAIT_GENERATION_TEXT, GEN_SUCCESS_TEXT, UPSELL_VOICE_TEXT
)
from app.bot.keyboards.common import get_cancel_keyboard, get_confirm_keyboard, get_main_menu_keyboard
from app.bot.keyboards.payments import get_payment_keyboard
from app.application.use_cases.create_order import CreateOrderUseCase
from app.application.use_cases.start_payment import StartPaymentUseCase
from app.infra.db.repositories.order_repo import OrderRepo
from app.infra.db.repositories.stage_repo import StageRepo
from app.infra.db.repositories.config_repo import ConfigRepo
from app.infra.db.repositories.payment_repo import PaymentRepo
from app.infra.db.repositories.user_repo import UserRepo
from app.infra.payments.yookassa import YooKassaClient
from app.infra.db.session import async_session_factory
from app.infra.db.models import Artifact
import asyncio
from aiogram import Bot

router = Router()
logger = logging.getLogger(__name__)

async def poll_for_generation_result(bot: Bot, user_id: int, stage_id: UUID, session_pool, state: FSMContext):
    logger.info(f"Starting background polling for stage {stage_id}")
    for _ in range(15):
        await asyncio.sleep(2)
        async with session_pool() as session:
            result = await session.execute(
                select(Artifact).where(Artifact.stage_id == stage_id)
            )
            artifact = result.scalars().first()
            
            if artifact:
                logger.info(f"Artifact found for stage {stage_id} in background polling")
                await state.set_state(PoemFlow.upsell_offer)
                await bot.send_message(
                    chat_id=user_id,
                    text=GEN_SUCCESS_TEXT.format(poem_text=artifact.storage_key),
                    reply_markup=get_main_menu_keyboard()
                )
                await bot.send_message(chat_id=user_id, text=UPSELL_VOICE_TEXT)
                return
    logger.info(f"Background polling finished for stage {stage_id} without result")

@router.message(F.text == "📝 Заказать стих")
async def start_poem_flow(message: types.Message, state: FSMContext):
    await state.set_state(PoemFlow.poem_occasion)
    await message.answer(POEM_OCCASION_TEXT, reply_markup=get_cancel_keyboard())

@router.message(F.text == "❌ Отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(CANCELLED_TEXT, reply_markup=get_main_menu_keyboard())

@router.message(PoemFlow.poem_occasion)
async def process_occasion(message: types.Message, state: FSMContext):
    await state.update_data(occasion=message.text)
    await state.set_state(PoemFlow.poem_recipient)
    await message.answer(POEM_RECIPIENT_TEXT)

@router.message(PoemFlow.poem_recipient)
async def process_recipient(message: types.Message, state: FSMContext):
    await state.update_data(recipient=message.text)
    await state.set_state(PoemFlow.poem_details)
    await message.answer(POEM_DETAILS_TEXT)

@router.message(PoemFlow.poem_details)
async def process_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text)
    data = await state.get_data()
    
    await state.set_state(PoemFlow.poem_confirm)
    await message.answer(
        CONFIRM_ORDER_TEXT.format(
            occasion=data['occasion'],
            recipient=data['recipient'],
            details=data['details']
        ),
        reply_markup=get_confirm_keyboard()
    )

@router.callback_query(F.data == "confirm_order", PoemFlow.poem_confirm)
async def confirm_order(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    logger.info(f"Confirming order for user {callback.from_user.id}")
    try:
        data = await state.get_data()
        user_repo = UserRepo(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        
        if not user:
            logger.error(f"User {callback.from_user.id} not found in DB")
            await callback.answer("Ошибка: пользователь не найден. Попробуйте /start", show_alert=True)
            return

        # Use cases
        order_repo = OrderRepo(session)
        stage_repo = StageRepo(session)
        config_repo = ConfigRepo(session)
        payment_repo = PaymentRepo(session)
        
        create_order_uc = CreateOrderUseCase(order_repo, stage_repo, config_repo)
        stage = await create_order_uc.execute(user.id, data)
        
        # ТЕСТОВЫЙ ЗАПУСК: Пропускаем оплату и сразу запускаем генерацию
        logger.info(f"TEST MODE: Skipping payment for stage {stage.id} and starting generation...")
        
        # Обновляем статус этапа на PAID (имитация оплаты)
        stage.status = OrderStageStatus.PAID
        await session.commit()
        logger.info(f"Order created and paid: {stage.order_id}, stage: {stage.id}")
        
        # Запускаем задачу генерации с защитой от зависания, если Redis недоступен
        try:
            from app.infra.queue.tasks import generate_poem_task
            generate_poem_task.apply_async(args=[str(stage.id)], connect_timeout=2)
            logger.info(f"Task sent to queue for stage {stage.id}")
        except Exception as e:
            logger.error(f"Failed to send task to Celery: {e}. Is Redis running?")
            # Мы не прерываем процесс, так как заказ уже создан и помечен как оплаченный.
            # В реальном приложении здесь можно было бы уведомить админа.
        
        await state.update_data(order_id=str(stage.order_id), stage_id=str(stage.id))
        await state.set_state(PoemFlow.await_generation)
        
        await callback.message.edit_text(
            AWAIT_PAYMENT_TEXT.format(price=stage.price / 100),
            reply_markup=get_payment_keyboard(
                payment_url="https://test.yookassa.ru/...", # В тесте URL заглушка
                check_callback="check_payment"
            )
        )
        return # Останавливаем тут, чтобы не уходить в генерацию без оплаты (хотя в коде ниже имитация)
        
        await callback.message.edit_text(
            AWAIT_GENERATION_TEXT,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Проверить готовность", callback_data="check_gen")]
            ])
        )
        logger.info(f"Bot is now waiting for generation results for stage {stage.id}.")
        
        # Start background polling
        asyncio.create_task(
            poll_for_generation_result(
                bot=callback.bot,
                user_id=callback.from_user.id,
                stage_id=stage.id,
                session_pool=async_session_factory,
                state=state
            )
        )
            
        await callback.answer()
    except Exception as e:
        logger.exception(f"Error in confirm_order: {e}")
        await callback.answer("Произошла ошибка. Попробуйте еще раз или обратитесь в поддержку.", show_alert=True)

@router.callback_query(F.data == "change_order", PoemFlow.poem_confirm)
async def change_order(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(PoemFlow.poem_occasion)
    await callback.message.answer(POEM_OCCASION_TEXT, reply_markup=get_cancel_keyboard())
    await callback.answer()

@router.callback_query(F.data == "cancel_order", PoemFlow.poem_confirm)
async def cancel_order_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(CANCELLED_TEXT)
    await callback.answer()

@router.callback_query(F.data == "check_payment", PoemFlow.await_payment)
async def check_payment_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    stage_id = UUID(data['stage_id'])
    
    stage_repo = StageRepo(session)
    stage = await stage_repo.get_by_id(stage_id)
    
    if stage.status in [OrderStageStatus.PAID, OrderStageStatus.QUEUED, OrderStageStatus.PROCESSING, OrderStageStatus.COMPLETED]:
        await state.set_state(PoemFlow.await_generation)
        await callback.message.edit_text(
            AWAIT_GENERATION_TEXT,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Проверить готовность", callback_data="check_gen")]
            ])
        )
        
        # Start background polling
        asyncio.create_task(
            poll_for_generation_result(
                bot=callback.bot,
                user_id=callback.from_user.id,
                stage_id=stage_id,
                session_pool=async_session_factory,
                state=state
            )
        )
    else:
        await callback.answer("Оплата еще не подтверждена. Попробуйте через минуту.", show_alert=True)

async def check_generation_status(message: types.Message, state: FSMContext, session: AsyncSession):
    logger.info("check_generation_status called")
    data = await state.get_data()
    stage_id = UUID(data['stage_id'])
    
    result = await session.execute(
        select(Artifact).where(Artifact.stage_id == stage_id)
    )
    artifact = result.scalars().first()
    
    if artifact:
        await state.set_state(PoemFlow.upsell_offer)
        await message.answer(
            GEN_SUCCESS_TEXT.format(poem_text=artifact.storage_key), # storage_key stores text for POEM artifact type in Итерация 3
            reply_markup=get_main_menu_keyboard()
        )
        await message.answer(UPSELL_VOICE_TEXT)
    else:
        # Повторим проверку через 10 секунд (в aiogram это обычно делается через scheduler, но тут для простоты)
        await message.answer("Стихотворение еще генерируется... Нажмите 'Проверить готовность'",
                           reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                               [types.InlineKeyboardButton(text="🔄 Проверить готовность", callback_data="check_gen")]
                           ]))

@router.callback_query(F.data == "check_gen", PoemFlow.await_generation)
async def check_gen_callback(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    await check_generation_status(callback.message, state, session)
    await callback.answer()