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
    # Твій чистий домен Cloudflare (БЕЗ https://)
    CF_DOMAIN = "bybit-proxy.itconsultaustria.workers.dev"

    try:
        session = HTTP(
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
            domain=CF_DOMAIN
        )

        # Захардкоджені параметри для тесту
        symbol = "BTCUSDT"
        side = "Sell"  # Шорт
        leverage = "10"  # Плече
        qty = "0.001"  # Мінімальна кількість для BTC

        print(f"--- Спроба відкрити ордер: {symbol} {side} ---")

        # 1. Встановлюємо плече
        try:
            session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage=leverage,
                sellLeverage=leverage,
            )
            print("✅ Плече встановлено/перевірено")
        except Exception as e:
            print(f"ℹ️ Плече (можливо, вже стоїть): {e}")

        # 2. Маркет ордер
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=qty,
            timeInForce="GTC",
        )
        return True, order

    except Exception as e:
        return False, str(e)