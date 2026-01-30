import asyncio
import io
import re
import json
import difflib
import importlib.util
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from bybit_trade import place_bybit_order
from test_trade import place_test_order

# Налаштування для aiogram 3
from pydantic import ConfigDict

ConfigDict.protected_namespaces = ()

# Імпорт конфігу
CONFIG_PATH = Path('/home/olekarp/config.py')
spec = importlib.util.spec_from_file_location("user_config", str(CONFIG_PATH))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

bot = Bot(token=config.TG_TOKEN)
dp = Dispatcher()
thread_pool = ThreadPoolExecutor(max_workers=4)
TICKERS_DB = Path(__file__).resolve().parent / 'tickers_db.json'


class TradeState(StatesGroup):
    waiting_for_ticker = State()
    waiting_for_leverage = State()


def load_db():
    if TICKERS_DB.exists():
        with open(TICKERS_DB, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_to_db(ocr_name, correct_name):
    db = load_db()
    db[ocr_name.upper()] = correct_name.upper()
    with open(TICKERS_DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4)


def get_best_ticker(ocr_name):
    db = load_db()
    name = ocr_name.upper()
    if name in db: return db[name]
    known = list(set(db.values())) + ["BTC", "ETH", "SOL", "1000RATS", "MERL"]
    matches = difflib.get_close_matches(name, known, n=1, cutoff=0.5)
    return matches[0] if matches else None


# --- OCR ПАРСИНГ (Тільки монета, напрямок та вхід) ---
def process_ocr(image_bytes):
    from PIL import Image, ImageOps
    import pytesseract

    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size

    # Визначаємо Long/Short по кольору
    direction_area = img.crop((width * 0.45, 5, width * 0.70, height * 0.12))
    stat = direction_area.resize((1, 1)).getpixel((0, 0))
    direction = "Short" if stat[0] > stat[1] else "Long"

    # Покращуємо для тексту
    gray = ImageOps.grayscale(img.resize((width * 2, height * 2)))
    enhanced = gray.point(lambda x: 0 if x < 160 else 255, '1')
    raw_text = pytesseract.image_to_string(enhanced, lang='eng+rus', config='--psm 6')
    clean_text = "".join(raw_text.split())

    # Тікер
    t_match = re.search(r'([A-Z0-9]{2,})USDT', clean_text, re.IGNORECASE)
    raw_coin = t_match.group(1).upper() if t_match else "UNKNOWN"

    # Ціна входу (шукаємо довге число)
    prices = re.findall(r'\d+\.\d{4,}', clean_text)
    entry = prices[0] if prices else "0"

    return {'raw_coin': raw_coin, 'direction': direction, 'entry': entry}


# --- ОБРОБНИКИ ---


@dp.message(F.text == "1")  # Напиши боту слово "тест"
async def debug_order_trigger(message: types.Message):
    print("LOG: Команда 'тест' отримана в коді!")  # <--- Додай це
    await message.answer("🛠 Запускаю тестовий ордер на Demo через Cloudflare...")

    # Запускаємо в окремому потоці, щоб не фрізити бота
    success, result = await asyncio.get_event_loop().run_in_executor(
        thread_pool, place_test_order
    )

    if success:
        order_id = result.get('result', {}).get('orderId', 'Н/Д')
        await message.answer(f"✅ УСПІХ!\nID Ордера: `{order_id}`\nПеревір Demo-акаунт.")
    else:
        await message.answer(f"❌ ПОМИЛКА:\n`{result}`")

@dp.message(F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    content = await bot.download_file(file.file_path)

    # Виконуємо OCR
    data = await asyncio.get_event_loop().run_in_executor(thread_pool, process_ocr, content.read())

    # Шукаємо в базі виправлень
    suggested = get_best_ticker(data['raw_coin'])

    # Якщо в базі немає (suggested is None), використовуємо те, що розпарсило
    final_suggestion = suggested if suggested else (data['raw_coin'] if data['raw_coin'] != "UNKNOWN" else None)

    await state.update_data(ocr_data=data, raw_ocr=data['raw_coin'])

    builder = InlineKeyboardBuilder()

    if final_suggestion:
        # Якщо назва виглядає правильно, даємо кнопку з цією назвою
        builder.button(text=f"✅ {final_suggestion}", callback_data=f"confirm_{final_suggestion}")

    builder.button(text="⌨️ Ввести вручну", callback_data="manual")
    builder.adjust(1)

    # Формуємо текст повідомлення
    status_text = f"🔍 Розпізнано: **{data['raw_coin']}**"
    if suggested:
        status_text += f"\n💡 Знайдено в базі як: **{suggested}**"

    await message.answer(
        f"{status_text}\n"
        f"📊 Напрямок: **{data['direction'].upper()}**\n"
        f"📥 Вхід: `{data['entry']}`\n\n"
        f"Використовуємо тікер **{final_suggestion or '???'}**?",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(TradeState.waiting_for_ticker)


@dp.callback_query(F.data == "manual")
async def ask_manual(callback: types.CallbackQuery):
    await callback.message.answer("Введіть тікер монети:")
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_ticker(callback: types.CallbackQuery, state: FSMContext):
    ticker = callback.data.split("_")[1].upper()
    await show_leverage_grid(callback.message, ticker, state)
    await callback.answer()


@dp.message(TradeState.waiting_for_ticker)
async def manual_ticker_input(message: types.Message, state: FSMContext):
    ticker = message.text.upper().strip()
    s_data = await state.get_data()
    if s_data.get('raw_ocr') and s_data['raw_ocr'] != "UNKNOWN":
        save_to_db(s_data['raw_ocr'], ticker)
    await show_leverage_grid(message, ticker, state)


async def show_leverage_grid(message, ticker, state: FSMContext):
    await state.update_data(final_ticker=ticker)

    # Створюємо сітку вибору плеча
    builder = InlineKeyboardBuilder()
    leverages = ["5", "10", "15", "20", "25"]
    for lev in leverages:
        builder.button(text=f"{lev}x", callback_data=f"lev_{lev}")

    builder.adjust(3)  # Кнопки по 3 в ряд
    await message.answer(f"Оберіть плече для **{ticker}**:", reply_markup=builder.as_markup())
    await state.set_state(TradeState.waiting_for_leverage)


# ... (попередній код залишається без змін)

@dp.callback_query(F.data.startswith("lev_"), TradeState.waiting_for_leverage)
async def ask_confirmation(callback: types.CallbackQuery, state: FSMContext):
    lev = callback.data.split("_")[1]
    data = await state.get_data()
    ticker = data['final_ticker']
    ocr = data['ocr_data']

    # Зберігаємо обране плече
    await state.update_data(final_leverage=lev)

    # Готуємо кнопки підтвердження
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ ТАК, відправляй", callback_data="order_confirm")
    builder.button(text="❌ НІ, скасувати", callback_data="order_cancel")
    builder.adjust(2)

    summary = (
        f"📋 **ПЕРЕВІРКА ОРДЕРА**\n\n"
        f"🔹 Монета: `{ticker}`\n"
        f"🔹 Напрямок: **{ocr['direction'].upper()}**\n"
        f"🔹 Плече: `{lev}x`\n"
        f"🔹 Ціна входу: `{ocr['entry']}`\n\n"
        f"🚀 **Відправляємо на Bybit?**"
    )

    await callback.message.edit_text(summary, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await callback.answer()


# Обробка натискання "ТАК"
@dp.callback_query(F.data == "order_confirm")
async def execute_order(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ticker = data['final_ticker']
    ocr = data['ocr_data']
    lev = data['final_leverage']

    # Виклик логіки Bybit
    # Перетворюємо Long/Short у формати Bybit: Buy/Sell
    side = "Buy" if ocr['direction'].lower() == "long" else "Sell"

    success, result = await asyncio.get_event_loop().run_in_executor(
        thread_pool,
        place_bybit_order,
        ticker, side, lev, ocr['entry']
    )

    if success:
        await callback.message.edit_text(
            f"✅ **Успіх!**\nОрдер для `{ticker}` ({lev}x) відкрит на Bybit.\nID: `{result['result']['orderId']}`"
        )
    else:
        await callback.message.edit_text(f"❌ **Помилка Bybit:**\n`{result}`")

    await state.clear()
    await callback.answer()


# Обробка скасування
@dp.callback_query(F.data == "order_cancel")
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Ордер скасовано. Чекаю на новий скріншот.")
    await state.clear()
    await callback.answer()


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))