import logging
import re
from uuid import UUID
from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.texts.ru import MY_ORDERS_EMPTY_TEXT, MY_ORDERS_HEADER_TEXT, ORDER_INFO_TEMPLATE
from app.infra.db.repositories.order_repo import OrderRepo
from app.infra.db.repositories.user_repo import UserRepo
from app.domain.enums import OrderStageStatus, ArtifactType

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "👤 Мои заказы")
async def cmd_my_orders(message: types.Message, session: AsyncSession):
    logger.info(f"User {message.from_user.id} requested their orders")
    
    user_repo = UserRepo(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer(MY_ORDERS_EMPTY_TEXT)
        return

    order_repo = OrderRepo(session)
    orders = await order_repo.get_user_orders(user.id)
    
    if not orders:
        await message.answer(MY_ORDERS_EMPTY_TEXT)
        return

    await message.answer(MY_ORDERS_HEADER_TEXT, parse_mode="Markdown")
    
    for order in orders:
        # Пытаемся определить общий статус по этапам
        status = "⏳ В обработке"
        is_completed = False
        if not order.stages:
            status = "🆕 Новый"
        elif all(s.status == OrderStageStatus.COMPLETED for s in order.stages):
            status = "✅ Завершен"
            is_completed = True
        elif any(s.status == OrderStageStatus.CANCELLED for s in order.stages):
            status = "❌ Отменен"
        elif any(s.status in [OrderStageStatus.PAID, OrderStageStatus.PROCESSING] for s in order.stages):
            status = "💳 Оплачен (в генерации)"
        elif any(s.status == OrderStageStatus.PENDING for s in order.stages):
            status = "🕒 Ожидает оплаты"

        # Ищем текст стиха в артефактах
        poem_ready_text = ""
        has_poem = False
        for art in order.artifacts:
            if art.type == ArtifactType.TEXT:
                poem_ready_text = "\n📝 Стих готов!"
                has_poem = True
                break

        order_info = ORDER_INFO_TEMPLATE.format(
            order_id=str(order.id)[:8],
            date=order.created_at.strftime("%d.%m.%Y %H:%M"),
            status=status,
            details=poem_ready_text
        )
        
        reply_markup = None
        if is_completed and has_poem:
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Скачать .txt", callback_data=f"dl_poem_{order.id}")]
            ])

        await message.answer(order_info, parse_mode="Markdown", reply_markup=reply_markup)

@router.callback_query(F.data.startswith("dl_poem_"))
async def process_download_poem(callback: types.CallbackQuery, session: AsyncSession):
    order_id_str = callback.data.replace("dl_poem_", "")
    try:
        order_id = UUID(order_id_str)
    except ValueError:
        await callback.answer("Ошибка: некорректный ID заказа", show_alert=True)
        return

    order_repo = OrderRepo(session)
    order = await order_repo.get_order_with_artifacts(order_id)

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    # Ищем текстовый артефакт
    poem_text = None
    for art in order.artifacts:
        if art.type == ArtifactType.TEXT:
            poem_text = art.storage_key
            break

    if not poem_text:
        await callback.answer("Стих еще не готов или не найден", show_alert=True)
        return

    # Формируем имя файла из первой строки
    first_line = poem_text.strip().split('\n')[0]
    # Очищаем от запрещенных символов
    filename = re.sub(r'[\\/*?:"<>|]', "", first_line)[:50] or "poem"
    filename += ".txt"

    # Отправляем файл
    file_content = poem_text.encode('utf-8')
    input_file = BufferedInputFile(file_content, filename=filename)
    
    await callback.message.answer_document(
        document=input_file,
        caption=f"📄 Ваш стих: {filename}"
    )
    await callback.answer()