import asyncio
import importlib
from pathlib import Path

from pybit.unified_trading import HTTP

# Імпорт конфігу
CONFIG_PATH = Path('/home/olekarp/config.py')
spec = importlib.util.spec_from_file_location("user_config", str(CONFIG_PATH))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def place_test_order():
    # Твоє повне посилання на воркер
    CF_WORKER_URL = "https://bybit-proxy.itconsultaustria.workers.dev"

    try:
        # Створюємо сесію БЕЗ параметра domain, але з явним endpoint
        session = HTTP(
            demo=True,
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
            # Вказуємо endpoint прямо, це обходить автоматичне додавання "api."
            endpoint=CF_WORKER_URL
        )

        symbol = "BTCUSDT"
        side = "Sell"
        leverage = "10"
        qty = "0.001"

        print(f"--- Тест через endpoint: {CF_WORKER_URL} ---")

        # 1. Плече
        try:
            session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=leverage,
                sellLeverage=leverage,
            )
        except Exception as e:
            print(f"Leverage note: {e}")

        # 2. Ордер
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
        )
        return True, order

    except Exception as e:
        return False, str(e)