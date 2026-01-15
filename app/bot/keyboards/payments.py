from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_payment_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Оплатить 49₽", url=payment_url)
            ],
            [
                InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")
            ]
        ]
    )