from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import gspread

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Внести рацпредложение", callback_data="suggestion")
    builder.button(text="🛠️ Добавить изделие (ремонт)", callback_data="repair")
    builder.adjust(1)
    return builder.as_markup()

async def get_repair_items_keyboard(worksheet: gspread.Worksheet) -> InlineKeyboardMarkup:
    # Получаем все названия из столбца A (со 2 строки, т.к. 1-я заголовок)
    try:
        all_items = worksheet.col_values(1)[1:]  # список, может быть пустым
    except:
        all_items = []
    unique_items = sorted(set([item for item in all_items if item.strip() != ""]))
    builder = InlineKeyboardBuilder()
    for item in unique_items:
        builder.button(text=item, callback_data=f"select_item_{item}")
    builder.button(text="➕ Добавить новое изделие", callback_data="add_new_item")
    builder.adjust(1)
    return builder.as_markup()