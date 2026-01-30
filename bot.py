import asyncio
import sys
import os
import re
import json
import io
import difflib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from PIL import Image, ImageOps
import pytesseract

# Додаємо верхню директорію в шлях для імпорту config
sys.path.append(str(Path(__file__).resolve().parent.parent))
try:
    import config
except ImportError:
    exit("❌ Помилка: Не знайдено файл config.py рівнем вище.")

# --- НАЛАШТУВАННЯ ---
BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR / 'tickers.json'
bot = Bot(token=config.TG_TOKEN)
dp = Dispatcher()
executor = ThreadPoolExecutor()  # Для неблокуючого OCR


def load_tickers():
    if JSON_FILE.exists():
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return sorted(json.load(f))
    return ["BTC", "ETH", "SOL"]


def save_ticker(ticker):
    tickers = set(load_tickers())
    tickers.add(ticker.upper().strip())
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(tickers)), f, indent=4)


# --- АСИНХРОННИЙ ПАРСИНГ ---
def sync_parse_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size

    # OCR монети
    coin_zone = img.crop((width * 0.02, height * 0.01, width // 1.5, height // 10))
    coin_zone = ImageOps.invert(coin_zone.convert('L')).point(lambda x: 0 if x < 140 else 255, '1')
    raw_coin = pytesseract.image_to_string(coin_zone, lang='eng', config='--psm 7').strip()
    raw_coin = re.sub(r'[^A-Z0-9]', '', raw_coin.upper()).replace("USDT", "")

    # Колір (Long/Short)
    check_area = img.crop((width // 2, 0, width, height // 4))
    r, g, b = ImageOps.posterize(check_area.resize((1, 1)), 1).getpixel((0, 0))
    direction = "🔴 SHORT" if r > g else "🟢 LONG"

    full_text = pytesseract.image_to_string(img, lang='eng')
    roi = re.search(r'([+-]?\d+[\.,]\d+\s*%)', full_text)
    prices = re.findall(r'\d+[\.,]\d{4,}', full_text)

    return {
        'raw_coin': raw_coin,
        'direction': direction,
        'roi': roi.group(1) if roi else "???",
        'entry': prices[0] if len(prices) > 0 else "-",
        'mark': prices[1] if len(prices) > 1 else "-"
    }


# --- ОБРОБНИКИ ---
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    content = await bot.download_file(file.file_path)

    # Запускаємо важкий OCR в окремому потоці
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(executor, sync_parse_image, content.read())

    tickers = load_tickers()
    best_matches = difflib.get_close_matches(data['raw_coin'], tickers, n=1, cutoff=0.4)
    suggestion = best_matches[0] if best_matches else None

    # Клавіатура
    builder = InlineKeyboardBuilder()
    for t in tickers[:15]:  # Обмежуємо кількість кнопок для швидкості
        builder.button(text=t, callback_data=f"sel_{t}")
    builder.button(text="➕ Додати нову", callback_data="add_new")
    builder.adjust(3)

    text = (f"🔍 OCR: `{data['raw_coin']}`\n"
            f"{f'🤔 Схоже на: *{suggestion}*' if suggestion else ''}\n"
            f"Оберіть монету:")

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@dp.callback_query(F.data.startswith("sel_"))
async def select_ticker(callback: types.CallbackQuery):
    ticker = callback.data.split("_")[1]
    # Тут можна додати логіку виводу фінального результату
    await callback.message.edit_text(f"✅ Обрано: **{ticker}**", parse_mode="Markdown")


async def main():
    print("🚀 Бот запущений асинхронно...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())