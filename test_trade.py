import importlib
from pathlib import Path

# Імпорт конфігу
CONFIG_PATH = Path('/home/olekarp/config.py')
spec = importlib.util.spec_from_file_location("user_config", str(CONFIG_PATH))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


import aiohttp
import hmac
import hashlib
import time
import json


async def place_test_order_async():
    # ПРЯМИЙ URL (для платного акаунта PythonAnywhere)
    # Demo: https://api-demo.bybit.com
    # Mainnet: https://api.bybit.com
    url = "https://api-demo.bybit.com/v5/order/create"

    # Важливо: Ключі мають бути від DEMO аккаунта, якщо йдете на api-demo
    payload = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "side": "Sell",
        "orderType": "Market",
        "qty": "0.001",
        "timeInForce": "GTC"
    }

    # Суворе форматування JSON (без пробілів) для підпису
    payload_str = json.dumps(payload, separators=(',', ':'))

    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"

    # Розрахунок підпису за стандартом V5
    param_str = timestamp + config.API_KEY + recv_window + payload_str
    signature = hmac.new(
        config.API_SECRET.encode("utf-8"),
        param_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    headers = {
        'X-BAPI-API-KEY': config.API_KEY,
        'X-BAPI-SIGN': signature,
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    # На платному тарифі trust_env не завадить, але проксі вже не лімітують
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=payload_str, timeout=10) as resp:
                status = resp.status
                # Читаємо як текст, щоб уникнути помилок декодування aiohttp
                text = await resp.text()

                print(f"DEBUG: Status {status}")
                print(f"DEBUG: Response: {text}")

                if status == 200:
                    return True, json.loads(text)
                else:
                    return False, f"Bybit Error {status}: {text}"
        except Exception as e:
            return False, f"Network Error: {str(e)}"