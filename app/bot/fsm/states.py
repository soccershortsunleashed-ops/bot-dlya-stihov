from aiogram.fsm.state import StatesGroup, State

class PoemFlow(StatesGroup):
    choose_product = State()
    poem_occasion = State()
    poem_recipient = State()
    poem_details = State()
    poem_confirm = State()
    await_payment = State()
    await_generation = State()
    show_result = State()
    upsell_offer = State()