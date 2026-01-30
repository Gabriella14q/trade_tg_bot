import importlib
from pathlib import Path

from pybit.unified_trading import HTTP

from pydantic import ConfigDict

ConfigDict.protected_namespaces = ()

# Імпорт конфігу
CONFIG_PATH = Path('/home/olekarp/config.py')
spec = importlib.util.spec_from_file_location("user_config", str(CONFIG_PATH))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

def place_bybit_order(ticker, side, leverage, entry_price):
    # Твоє посилання, яке ти отримав у Cloudflare

    try:
        # Створюємо сесію через проксі
        session = HTTP(
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
            domain='https://bybit-proxy.itconsultaustria.workers.dev/'  # Весь трафік іде через Cloudflare на api-demo.bybit.com
        )

        # Очищення тікера (якщо MERLU -> MERL)
        clean_ticker = ticker.replace("USDT", "").strip()
        if clean_ticker.endswith('U') and len(clean_ticker) > 4:
            clean_ticker = clean_ticker[:-1]

        symbol = f"{clean_ticker}USDT"

        # Встановлення плеча
        try:
            session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage),
            )
        except Exception as e:
            print(f"Плече вже встановлено або помилка: {e}")

        # Розрахунок кількості (наприклад, на 10 USDT з урахуванням плеча)
        # Формула: (Сума в USDT * Плече) / Ціна входу
        qty = round((10 * int(leverage)) / float(entry_price), 1)

        # Відправка маркет-ордера
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=str(qty),
            timeInForce="GTC",
        )
        return True, order

    except Exception as e:
        return False, str(e)
