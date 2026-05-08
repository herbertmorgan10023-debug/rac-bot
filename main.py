import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import gspread
from google.oauth2.service_account import Credentials

from states import SuggestionStates, RepairStates
from keyboards import get_main_menu_keyboard, get_repair_items_keyboard

# === КОНФИГУРАЦИЯ (ЗАМЕНИТЕ НА СВОИ ЗНАЧЕНИЯ) ===
BOT_TOKEN = os.getenv("BOT_TOKEN")  # на Render будет через env
SPREADSHEET_KEY = "ВСТАВЬТЕ_КЛЮЧ_ТАБЛИЦЫ"   # например "1abcde..."
SHEET_SUGGESTION = "Рацпредложения"
SHEET_REPAIR = "РемонтныеРаботы"
KEY_FILE_NAME = "google_key.json"   # имя вашего json-файла
# ============================================

# Подключение к Google Sheets
def get_worksheet(sheet_name: str):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(KEY_FILE_NAME, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_KEY)
    return spreadsheet.worksheet(sheet_name)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Получаем объекты листов (один раз при старте, но будем пересоздавать, т.к. файл может обновиться?
# Для простоты будем получать каждый раз внутри функций)
# Но для списка изделий нужен свежий лист, поэтому будем вызывать get_worksheet

# ========== ГЛАВНОЕ МЕНЮ ==========
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Выберите действие:", reply_markup=get_main_menu_keyboard())

# ========== РАЦПРЕДЛОЖЕНИЯ (аналог предыдущего бота) ==========
@dp.callback_query(F.data == "suggestion")
async def start_suggestion(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название рацпредложения:")
    await state.set_state(SuggestionStates.waiting_for_title)
    await callback.answer()

@dp.message(SuggestionStates.waiting_for_title)
async def process_suggestion_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(SuggestionStates.waiting_for_number)
    await message.answer("Введите номер предложения (цифры или текст):")

@dp.message(SuggestionStates.waiting_for_number)
async def process_suggestion_number(message: Message, state: FSMContext):
    await state.update_data(number=message.text)
    await state.set_state(SuggestionStates.waiting_for_author)
    await message.answer("Введите автора (исполнителя):")

@dp.message(SuggestionStates.waiting_for_author)
async def process_suggestion_author(message: Message, state: FSMContext):
    await state.update_data(author=message.text)
    await state.set_state(SuggestionStates.waiting_for_date)
    await message.answer("Введите дату в формате ДД.ММ.ГГГГ:")

@dp.message(SuggestionStates.waiting_for_date)
async def process_suggestion_date(message: Message, state: FSMContext):
    date_text = message.text
    try:
        datetime.strptime(date_text, "%d.%m.%Y")
    except ValueError:
        await message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ. Попробуйте ещё раз.")
        return
    data = await state.get_data()
    title = data["title"]
    number = data["number"]
    author = data["author"]
    try:
        ws = get_worksheet(SHEET_SUGGESTION)
        ws.append_row([title, number, author, date_text])
        await message.answer("✅ Рацпредложение добавлено в таблицу!")
    except Exception as e:
        await message.answer("❌ Ошибка при записи. Попробуйте позже.")
    await state.clear()

# ========== РЕМОНТНЫЕ РАБОТЫ (ДОБАВЛЕНИЕ ИЗДЕЛИЙ) ==========
@dp.callback_query(F.data == "repair")
async def start_repair(callback: CallbackQuery, state: FSMContext):
    # Показываем список существующих изделий
    ws_repair = get_worksheet(SHEET_REPAIR)
    keyboard = await get_repair_items_keyboard(ws_repair)
    await callback.message.edit_text("Выберите изделие или добавьте новое:", reply_markup=keyboard)
    # Не меняем состояние пока, ждем выбора
    await state.set_state(RepairStates.waiting_for_item_name)
    await callback.answer()

# Обработка выбора существующего изделия
@dp.callback_query(RepairStates.waiting_for_item_name, F.data.startswith("select_item_"))
async def repair_existing_item(callback: CallbackQuery, state: FSMContext):
    item = callback.data.split("select_item_", 1)[1]
    await state.update_data(item_name=item)
    await callback.message.edit_text(f"Выбрано: {item}\nВведите количество изготовленных единиц (только цифры):")
    await state.set_state(RepairStates.waiting_for_quantity)
    await callback.answer()

# Обработка добавления нового изделия
@dp.callback_query(RepairStates.waiting_for_item_name, F.data == "add_new_item")
async def repair_new_item(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название нового изделия:")
    # Остаемся в том же состоянии, но дальше поймем, что это новое
    await state.set_state(RepairStates.waiting_for_item_name)  # остаемся
    await callback.answer()

# Если пользователь вводит текст и находится в состоянии waiting_for_item_name (это значит, что он вводит новое изделие)
@dp.message(RepairStates.waiting_for_item_name)
async def repair_entering_new_item(message: Message, state: FSMContext):
    # Это новая позиция
    await state.update_data(item_name=message.text)
    await message.answer(f"Новое изделие «{message.text}» сохранено. Теперь введите количество:")
    await state.set_state(RepairStates.waiting_for_quantity)

@dp.message(RepairStates.waiting_for_quantity)
async def repair_quantity(message: Message, state: FSMContext):
    try:
        quantity = int(message.text)
    except:
        await message.answer("Пожалуйста, введите целое число (количество):")
        return
    await state.update_data(quantity=quantity)
    await message.answer("Введите месяц и год (например, Май 2026):")
    await state.set_state(RepairStates.waiting_for_month_year)

@dp.message(RepairStates.waiting_for_month_year)
async def repair_month_year(message: Message, state: FSMContext):
    month_year = message.text
    data = await state.get_data()
    item_name = data["item_name"]
    quantity = data["quantity"]
    # Записываем в лист "РемонтныеРаботы"
    try:
        ws = get_worksheet(SHEET_REPAIR)
        ws.append_row([item_name, quantity, month_year])
        await message.answer("✅ Данные о ремонтном изделии добавлены!")
    except Exception as e:
        await message.answer("❌ Ошибка записи в таблицу.")
    await state.clear()

# ========== ЗАПУСК ==========
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Бот запущен...")
    asyncio.run(main())