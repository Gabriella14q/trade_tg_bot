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
    try:
        # Твій Cloudflare Worker тепер виступає як проксі-сервер
        proxy_url = "https://bybit-proxy.itconsultaustria.workers.dev"

        session = HTTP(
            demo=True,  # Тепер це працює "з коробки"
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
            proxy=proxy_url  # Передаємо воркер як проксі
        )

        # Решта коду без змін
        order = session.place_order(
            category="linear",
            symbol="BTCUSDT",
            side="Sell",
            orderType="Market",
            qty="0.001"
        )
        return True, order
    except Exception as e:
        return False, str(e)