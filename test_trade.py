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
    # Твоє посилання на воркер (БЕЗ https://)
    # Ми будемо стукати прямо на нього
    url = "https://bybit-proxy.itconsultaustria.workers.dev/v5/order/create"

    api_key = config.API_KEY
    api_secret = config.API_SECRET

    # Дані ордера
    payload = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "side": "Sell",
        "orderType": "Market",
        "qty": "0.001",
        "timeInForce": "GTC"
    }

    # Створення підпису Bybit (це те, що pybit робить всередині)
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    payload_str = json.dumps(payload)
    param_str = timestamp + api_key + recv_window + payload_str
    hash = hmac.new(bytes(api_secret, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
    signature = hash.hexdigest()

    headers = {
        'X-BAPI-API-KEY': api_key,
        'X-BAPI-SIGN': signature,
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    try:
        # Шлемо запит прямо на Cloudflare
        response = requests.post(url, headers=headers, data=payload_str)
        result = response.json()

        if result.get('retCode') == 0:
            return True, result
        else:
            return False, f"Bybit Error: {result.get('retMsg')} (Code: {result.get('retCode')})"
    except Exception as e:
        return False, f"Request Error: {str(e)}"