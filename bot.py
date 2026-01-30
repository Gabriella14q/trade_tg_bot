import asyncio
import sys
import io
import re
import json
import difflib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from PIL import Image, ImageOps
import pytesseract

# --- ІМПОРТ КОНФІГУ (на рівень вище) ---
sys.path.append(str(Path(__file__).resolve().parent.parent))
try:
    import config

    TOKEN = config.TG_TOKEN
except (ImportError, AttributeError):
    print("❌ Помилка: Перевірте config.py на рівень вище та наявність TG_TOKEN")
    sys.exit(1)

# --- НАЛАШТУВАННЯ ---
BASE_DIR = Path(__file__).resolve().parent
JSON_FILE = BASE_DIR / 'tickers.json'
bot = Bot(token=TOKEN)
dp = Dispatcher()
thread_pool = ThreadPoolExecutor(max_workers=4)


def load_tickers():
    if JSON_FILE.exists():
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return sorted(json.load(f))
    return ["BTC", "ETH", "SOL", "XRP", "ADA"]


# --- OCR ЛОГІКА (Синхронна частина) ---
def process_ocr(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size

    # Зона монети
    coin_zone = img.crop((width * 0.02, height * 0.01, width // 1.5, height // 10))
    coin_zone = ImageOps.invert(coin_zone.convert('L')).point(lambda x: 0 if x < 140 else 255, '1')
    raw_coin = pytesseract.image_to_string(coin_zone, lang='eng', config='--psm 7').strip()
    raw_coin = re.sub(r'[^A-Z0-9]', '', raw_coin.upper()).replace("USDT", "")

    # Напрямок
    check_area = img.crop((width // 2, 0, width, height // 4))
    r, g, b = ImageOps.posterize(check_area.resize((1, 1)), 1).getpixel((0, 0))
    direction = "🔴 SHORT" if r > g else "🟢 LONG"

    # Текст
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


# --- ОБРОБНИКИ AIOGRAM ---
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    # Отримуємо фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    content = await bot.download_file(file.file_path)

    # Запускаємо OCR в окремому потоці, щоб не фрізити бота
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(thread_pool, process_ocr, content.read())

    tickers = load_tickers()
    best_matches = difflib.get_close_matches(data['raw_coin'], tickers, n=1, cutoff=0.4)
    suggestion = best_matches[0] if best_matches else None

    # Клавіатура
    builder = InlineKeyboardBuilder()
    for t in tickers[:12]:  # Перші 12 для компактності
        builder.button(text=t, callback_data=f"sel_{t}")
    builder.button(text="➕ Додати нову", callback_data="add_new")
    builder.adjust(3)

    res_text = (
        f"🔍 OCR розпізнав: `{data['raw_coin']}`\n"
        f"{f'🤔 Можливо це: **{suggestion}**?' if suggestion else '❌ Не в базі'}\n\n"
        f"📊 {data['direction']} | ROI: {data['roi']}\n"
        f"📥 Вхід: `{data['entry']}`\n\n"
        f"Підтвердіть монету зі списку:"
    )

    await message.answer(res_text, reply_markup=builder.as_markup(), parse_mode="Markdown")


@dp.callback_query(F.data.startswith("sel_"))
async def ticker_callback(callback: types.CallbackQuery):
    ticker = callback.data.split("_")[1]
    await callback.message.edit_text(f"✅ Готово! Монета **{ticker}** прийнята в роботу.", parse_mode="Markdown")
    await callback.answer()


async def main():
    print("🚀 Бот запущений (aiogram 3.x)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass