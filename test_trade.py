import asyncio
import importlib
import os
from pathlib import Path

from pybit.unified_trading import HTTP

# Імпорт конфігу
CONFIG_PATH = Path('/home/olekarp/config.py')
spec = importlib.util.spec_from_file_location("user_config", str(CONFIG_PATH))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def place_test_order():
    # Твоє посилання на воркер
    worker_url = "https://bybit-proxy.itconsultaustria.workers.dev"

    # Встановлюємо проксі на рівні системних змінних для цього процесу
    os.environ['HTTP_PROXY'] = worker_url
    os.environ['HTTPS_PROXY'] = worker_url

    try:
        # Тепер створюємо сесію максимально просто
        # Бібліотека САМА підхопить проксі з os.environ
        session = HTTP(
            demo=True,
            api_key=config.API_KEY,
            api_secret=config.API_SECRET
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
    finally:
        # Чистимо за собою, щоб не впливати на інші запити бота
        if 'HTTP_PROXY' in os.environ: del os.environ['HTTP_PROXY']
        if 'HTTPS_PROXY' in os.environ: del os.environ['HTTPS_PROXY']