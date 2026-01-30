import asyncio
import hashlib
import hmac
import importlib
import json
import os
import time
from pathlib import Path

import requests
from pybit.unified_trading import HTTP

# Імпорт конфігу
CONFIG_PATH = Path('/home/olekarp/config.py')
spec = importlib.util.spec_from_file_location("user_config", str(CONFIG_PATH))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


def place_test_order():
    # ПОВНЕ ПОСИЛАННЯ (перевір чи немає зайвих пробілів)
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
        bytes(config.API_SECRET, "utf-8"),
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

    try:
        session = requests.Session()
        session.trust_env = False  # Ігноруємо системні проксі PythonAnywhere

        response = session.post(url, headers=headers, data=payload_str, timeout=10)

        print(f"DEBUG: Status {response.status_code}")

        if not response.text:
            return False, "Cloudflare returned an empty response (0 bytes)."

        try:
            result = response.json()
            if result.get('retCode') == 0:
                return True, result
            else:
                return False, f"Bybit: {result.get('retMsg')} ({result.get('retCode')})"
        except:
            return False, f"Not a JSON. Status: {response.status_code}. Text: {response.text[:100]}"

    except Exception as e:
        return False, f"Connection Error: {str(e)}"