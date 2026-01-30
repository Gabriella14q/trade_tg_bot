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
    url = "https://bybit-proxy.itconsultaustria.workers.dev/v5/order/create"

    payload = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "side": "Sell",
        "orderType": "Market",
        "qty": "0.001",
        "timeInForce": "GTC"
    }

    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    payload_str = json.dumps(payload)

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
        'Content-Type': 'application/json',
        'Accept-Encoding': 'identity'  # Явно просимо не стискати
    }

    # ВАЖЛИВО: auto_decompress=False вимикає спроби aiohttp розпакувати Brotli
    async with aiohttp.ClientSession(auto_decompress=False, trust_env=True) as session:
        try:
            async with session.post(url, headers=headers, data=payload_str, timeout=10) as resp:
                # Читаємо як байтовий рядок
                raw_body = await resp.read()

                # Декодуємо вручну в текст
                try:
                    text_res = raw_body.decode('utf-8')
                    data = json.loads(text_res)
                    return True, data
                except Exception as parse_err:
                    # Якщо це все одно стиснутий бінарний мотлох
                    print(f"Raw body start: {raw_body[:20]}")
                    return False, f"Decode error: {parse_err}"

        except Exception as e:
            print(f"Мережева помилка: {e}")
            return False, str(e)