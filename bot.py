import telebot
from telebot import types
import pytesseract
from PIL import Image, ImageOps
import io
import re
import json
import os
import difflib

import config

# --- НАЛАШТУВАННЯ ---

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = os.path.join(BASE_DIR, 'tickers.json')

if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

bot = telebot.TeleBot(config.TOKEN)

# --- РОБОТА З БАЗОЮ ---
def load_tickers():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return sorted(json.load(f))
    return ["BTC", "ETH", "SOL"]


def save_ticker(ticker):
    ticker = ticker.upper().strip()
    tickers = load_tickers()
    if ticker not in tickers:
        tickers.append(ticker)
        with open(JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(tickers, f, indent=4)
    return sorted(tickers)


# --- ПАРСИНГ ---
def parse_crypto_data(image):
    width, height = image.size
    # Зона монети
    coin_zone = image.crop((width * 0.02, height * 0.01, width // 1.5, height // 10))
    coin_zone = ImageOps.invert(coin_zone.convert('L')).point(lambda x: 0 if x < 140 else 255, '1')
    raw_coin = pytesseract.image_to_string(coin_zone, lang='eng', config='--psm 7').strip()
    raw_coin = re.sub(r'[^A-Z0-9]', '', raw_coin.upper()).replace("USDT", "")

    # Напрямок (Short/Long)
    check_area = image.crop((width // 2, 0, width, height // 4))
    r, g, b = ImageOps.posterize(check_area.resize((1, 1)), 1).getpixel((0, 0))
    direction = "🔴 SHORT" if r > g else "🟢 LONG"

    # ROI та ціни
    full_text = pytesseract.image_to_string(image, lang='eng')
    roi = re.search(r'([+-]?\d+[\.,]\d+\s*%)', full_text)
    prices = re.findall(r'\d+[\.,]\d{4,}', full_text)

    return {
        'raw_coin': raw_coin,
        'direction': direction,
        'roi': roi.group(1) if roi else "???",
        'entry': prices[0] if len(prices) > 0 else "-",
        'mark': prices[1] if len(prices) > 1 else "-"
    }


user_sessions = {}


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        chat_id = message.chat.id
        file_info = bot.get_file(message.photo[-1].file_id)
        img = Image.open(io.BytesIO(bot.download_file(file_info.file_path)))

        data = parse_crypto_data(img)
        tickers = load_tickers()

        # Шукаємо найбільш схожу монету в нашому списку
        best_matches = difflib.get_close_matches(data['raw_coin'], tickers, n=1, cutoff=0.4)
        suggestion = best_matches[0] if best_matches else None

        user_sessions[chat_id] = data

        # Створюємо клавіатуру зі списком усіх монет
        markup = types.InlineKeyboardMarkup(row_width=3)
        btns = [types.InlineKeyboardButton(t, callback_data=f"sel_{t}") for t in tickers]
        markup.add(*btns)
        markup.add(types.InlineKeyboardButton("➕ Додати нову монету", callback_data="add_new"))

        text = f"🔍 OCR розпізнав: `{data['raw_coin']}`\n"
        if suggestion:
            text += f"🤔 Схоже на: *{suggestion}*?\n"
        text += "\nОберіть монету зі списку нижче:"

        bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Помилка: {e}")


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    if call.data.startswith("sel_"):
        ticker = call.data.replace("sel_", "")
        if chat_id in user_sessions:
            send_result(chat_id, ticker, user_sessions[chat_id])
        bot.delete_message(chat_id, call.message.message_id)

    elif call.data == "add_new":
        msg = bot.send_message(chat_id, "Введіть назву нової монети (напр. PEPE):")
        bot.register_next_step_handler(msg, process_new_ticker)
        bot.delete_message(chat_id, call.message.message_id)


def process_new_ticker(message):
    ticker = message.text.upper().strip()
    save_ticker(ticker)
    chat_id = message.chat.id
    if chat_id in user_sessions:
        send_result(chat_id, ticker, user_sessions[chat_id])
    else:
        bot.send_message(chat_id, f"✅ Монета {ticker} додана в базу!")


def send_result(chat_id, ticker, data):
    msg = (f"🪙 Монета: *{ticker}*\n"
           f"📊 Напрямок: *{data['direction']}*\n"
           f"💰 ROI: `{data['roi']}`\n"
           f"📥 Вхід: `{data['entry']}`\n"
           f"📈 Ціна: `{data['mark']}`")
    bot.send_message(chat_id, msg, parse_mode='Markdown')


if __name__ == "__main__":
    print("Бот працює...")
    bot.polling(none_stop=True)