from aiogram.fsm.state import State, StatesGroup

class SuggestionStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_number = State()
    waiting_for_author = State()
    waiting_for_date = State()

class RepairStates(StatesGroup):
    waiting_for_item_name = State()     # если ввод нового изделия
    waiting_for_quantity = State()
    waiting_for_month_year = State()