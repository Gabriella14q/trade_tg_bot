import importlib
from pathlib import Path

import requests
from pybit.unified_trading import HTTP

# Імпорт конфігу
CONFIG_PATH = Path('/home/olekarp/config.py')
spec = importlib.util.spec_from_file_location("user_config", str(CONFIG_PATH))
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

import requests
import json
import time
import hmac
import hashlib
import config


def place_test_order():
    # Твоя адреса Cloudflare
    url = "https://bybit-proxy.itconsultaustria.workers.dev/v5/order/create"

    payload = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "side": "Sell",
        "orderType": "Market",
        "qty": "0.001",
        "timeInForce": "GTC"
    }

    # Розрахунок підпису
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    payload_str = json.dumps(payload)
    param_str = timestamp + config.API_KEY + recv_window + payload_str
    signature = hmac.new(bytes(config.API_SECRET, "utf-8"), param_str.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = {
        'X-BAPI-API-KEY': config.API_KEY,
        'X-BAPI-SIGN': signature,
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    try:
        # Створюємо сесію, яка ігнорує змінні оточення (проксі)
        session = requests.Session()
        session.trust_env = False

        print("LOG: Відправляю запит на Cloudflare...")
        response = session.post(url, headers=headers, data=payload_str, timeout=15)

        print(f"LOG: Статус коду: {response.status_code}")
        print(f"LOG: Текст відповіді: {response.text}")

        return True, response.json()
    except Exception as e:
        print(f"LOG ERROR: {str(e)}")
        return False, str(e)