from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Заказать стих")],
            [KeyboardButton(text="👤 Мои заказы")]
        ],
        resize_keyboard=True
    )

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Все верно", callback_data="confirm_order"),
                InlineKeyboardButton(text="🔄 Изменить", callback_data="change_order")
            ],
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")
            ]
        ]
    )