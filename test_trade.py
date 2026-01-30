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
    # Твій домен БЕЗ https:// і БЕЗ api-demo (воркер сам знає куди слати)
    MY_CF_DOMAIN = "bybit-proxy.itconsultaustria.workers.dev"

    try:
        session = HTTP(
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
            domain=MY_CF_DOMAIN  # Бібліотека піде на ваш воркер, а він — на демо Bybit
        )

        order = session.place_order(
            category="linear",
            symbol="BTCUSDT",
            side="Sell",
            orderType="Market",
            qty="0.001",
            timeInForce="GTC"
        )
        return True, order
    except Exception as e:
        return False, str(e)