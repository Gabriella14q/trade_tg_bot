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
        session = HTTP(
            demo=True,
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
            # Вказуємо ТІЛЬКИ базову частину домену.
            # pybit сама додасть "api-demo." попереду.
            # Разом вийде: api-demo.itconsultaustria.workers.dev
            domain="itconsultaustria.workers.dev"
        )

        symbol = "BTCUSDT"
        qty = "0.001"

        # Плече
        session.set_leverage(
            category="linear",
            symbol=symbol,
            buyLeverage="10",
            sellLeverage="10",
        )

        # Ордер
        order = session.place_order(
            category="linear",
            symbol=symbol,
            side="Sell",
            orderType="Market",
            qty=qty,
        )
        return True, order

    except Exception as e:
        return False, str(e)