from pybit.unified_trading import HTTP
import config

def place_bybit_order(ticker, side, leverage, entry_price):
    """
    Функція для відкриття позиції на Futures (Unified Account)
    """
    try:
        session = HTTP(
            demo=True,
            api_key=config.API_KEY,
            api_secret=config.API_SECRET,
        )

        # 1. Встановлюємо плече
        session.set_leverage(
            category="linear",
            symbol=f"{ticker}USDT",
            buyLeverage=str(leverage),
            sellLeverage=str(leverage),
        )

        # 2. Відкриваємо маркет-ордер (найшвидший вхід)
        # Параметри qty (кількість) треба розрахувати залежно від твого депо
        # Для прикладу ставимо мінімалку або через USDT
        order = session.place_order(
            category="linear",
            symbol=f"{ticker}USDT",
            side=side,
            orderType="Market",
            qty="1", # ТУТ ТРЕБА ВКАЗАТИ КІЛЬКІСТЬ В МОНЕТАХ
            timeInForce="GTC",
        )
        return True, order
    except Exception as e:
        return False, str(e)