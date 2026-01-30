import importlib
from pathlib import Path

import requests
from pybit.unified_trading import HTTP

# Імпорт конфігу
CONFIG_PATH = Path('/home/olekarp/config.py')
spec = importlib.util.spec_from_file_location("user_config", str(CONFIG_PATH))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def place_test_order():
    # Твій домен Cloudflare
    MY_CF_DOMAIN = "bybit-proxy.itconsultaustria.workers.dev"

    print("LOG: Початок функції place_test_order")

    try:
        print(f"LOG: Підключення до домену: {MY_CF_DOMAIN}")
        session = HTTP(
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
            domain=MY_CF_DOMAIN
        )

        print("LOG: Спроба відправити ордер...")
        # Використовуємо спрощений виклик без встановлення плеча для тесту
        order = session.place_order(
            category="linear",
            symbol="BTCUSDT",
            side="Sell",
            orderType="Market",
            qty="0.001"
        )

        print(f"LOG: Отримано відповідь: {order}")
        return True, order

    except Exception as e:
        error_msg = f"LOG ERROR: {str(e)}"
        print(error_msg)
        return False, error_msg