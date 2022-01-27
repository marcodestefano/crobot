import threading
from decimal import Decimal, ROUND_DOWN, ROUND_UP
from croutils import *

TRADING_ENGINE_ACTIVE = 0
CRYPTO_CURRENCY_KEY = "CRYPTO_CURRENCY"
BASE_CURRENCY_KEY = "BASE_CURRENCY"
ORDER_TIME_INTERVAL_KEY = "ORDER_TIME_INTERVAL"
BUY_PRICE_FACTOR_KEY = "BUY_PRICE_FACTOR"
SELL_STRATEGY_KEY = "SELL_STRATEGY"
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"
ACTIVE_STATUS = "ACTIVE"
INTERVAL_1M = "1M"
PRODUCT_MIN_VALUE = "min"
PRODUCT_MAX_VALUE = "max"
TIME_INTERVAL_DAY = 86400
TIME_INTERVAL_MONTH = TIME_INTERVAL_DAY * 30
TIME_INTERVAL_QUARTER = TIME_INTERVAL_MONTH * 3
TIME_INTERVAL_SEMESTER = TIME_INTERVAL_QUARTER * 2
TIME_INTERVAL_YEAR = TIME_INTERVAL_DAY * 365
RATIO_1Y = Decimal(0.4)
RATIO_6M = Decimal(0.3)
RATIO_3M = Decimal(0.2)
RATIO_1M = Decimal(0.1)
TEST_MODE = Decimal(0.2)

def get_account_summary(currency = None):
    method = "private/get-account-summary"
    params = {}
    if currency:
        params["currency"] = currency
    result = query(method, params)
    return json.loads(result.text)

def get_available_quantity(currency):
    summary = get_account_summary(currency)
    available = 0
    if summary and summary["result"] and summary["result"]["accounts"]:
        available = summary["result"]["accounts"][0]["available"]
    return Decimal(str(available))

def get_ticker(crypto,base):
    method = "public/get-ticker"
    params = {
        "instrument_name" : create_pair(crypto,base)
    }
    result = publicquery(method, params)
    return json.loads(result.text)

def get_open_orders(crypto, base):
    method = "private/get-open-orders"
    params = {
        "instrument_name": create_pair(crypto, base),
    }
    result = query(method, params)
    return json.loads(result.text)

def is_buy_open_order(crypto, base):
    result = get_open_orders(crypto, base)
    buy_open_order = 0
    if result and result["result"]:
        for open_orders in result["result"]["order_list"]:
            if open_orders["side"] == SIDE_BUY and open_orders["status"] == ACTIVE_STATUS:
                buy_open_order = 1
                break
    return buy_open_order

def get_instrument(crypto,base):
    method = "public/get-instruments"
    result = publicquery(method)
    json_result = json.loads(result.text)
    instrument_result = None
    if (json_result and json_result["result"]):
        for instrument in json_result["result"]["instruments"]:
            if instrument["quote_currency"] == base and instrument["base_currency"] == crypto:
                instrument_result = instrument
    return instrument_result

def get_balance(base):
    total_value = 0
    summary = get_account_summary()
    if summary and summary["result"]:
        accounts = summary["result"]["accounts"]
        for account in accounts:
            if account["balance"] != 0:
                if account["currency"] == base:
                    total_value = total_value + account["balance"]
                else:
                    total_value = total_value + account["balance"]*get_current_price(account["currency"],base)
    return Decimal(str(total_value))

def get_current_price(crypto,base):
    result = get_ticker(crypto, base)
    current_price = None
    if (result and result["result"]):
        current_price = result["result"]["data"]["a"]
    return Decimal(str(current_price))

def create_order(crypto, base, side, price, quantity):
    method = "private/create-order"
    params = {
        "instrument_name": create_pair(crypto,base),
        "side": side,
        "type": "LIMIT",
        "exec_inst": "POST_ONLY",
        "price": float(price),
        "quantity": float(quantity),
        "time_in_force": "GOOD_TILL_CANCEL"
        }
    result = query(method, params)
    return json.loads(result.text)

def calculate_bid_price(crypto, base):
    result = get_ticker(crypto, base)
    buy_price = Decimal('-Inf')
    if (result and result["result"]):
        buy_price = Decimal(str(result["result"]["data"]["b"]))
    return buy_price

def calculate_ask_price(crypto, base):
    result = get_ticker(crypto, base)
    sell_price = Decimal('Inf')
    if (result and result["result"]):
        sell_price = Decimal(str(result["result"]["data"]["k"]))
    return sell_price

def get_product_min_max_value(crypto, base, interval):
    method = "public/get-candlestick"
    params = {
        "instrument_name": create_pair(crypto, base),
        "timeframe": INTERVAL_1M
    }
    result = publicquery(method, params)
    json_result = json.loads(result.text)

    min_max = {}
    min_max[PRODUCT_MIN_VALUE] = Decimal('Inf')
    min_max[PRODUCT_MAX_VALUE] = Decimal('-Inf')
    current_time = time.time()
    max_past = current_time - interval
    max_past = max_past * 1000
    if json_result and json_result["result"]:
        for candle in json_result["result"]["data"]:
            if max_past < candle["t"]:
                if min_max[PRODUCT_MIN_VALUE] > candle["l"]:
                    min_max[PRODUCT_MIN_VALUE] = candle["l"]
                if min_max[PRODUCT_MAX_VALUE] < candle["h"]:
                    min_max[PRODUCT_MAX_VALUE] = candle["h"]
    return min_max

def get_order_ratio(crypto, base):
    year_min_max = get_product_min_max_value(crypto, base, TIME_INTERVAL_YEAR)
    semester_min_max = get_product_min_max_value(crypto, base, TIME_INTERVAL_SEMESTER)
    quarter_min_max = get_product_min_max_value(crypto, base, TIME_INTERVAL_QUARTER)
    month_min_max = get_product_min_max_value(crypto, base, TIME_INTERVAL_MONTH)
    currentValue = get_current_price(crypto, base)
    ratio_1y = RATIO_1Y * getRatio(currentValue, year_min_max[PRODUCT_MIN_VALUE], year_min_max[PRODUCT_MAX_VALUE])
    ratio_6m = RATIO_6M * getRatio(currentValue, semester_min_max[PRODUCT_MIN_VALUE], semester_min_max[PRODUCT_MAX_VALUE])
    ratio_3m = RATIO_3M * getRatio(currentValue, quarter_min_max[PRODUCT_MIN_VALUE], quarter_min_max[PRODUCT_MAX_VALUE])
    ratio_1m = RATIO_1M * getRatio(currentValue, month_min_max[PRODUCT_MIN_VALUE], month_min_max[PRODUCT_MAX_VALUE])
    return ratio_1y + ratio_6m + ratio_3m + ratio_1m

def calculate_buy_quantity(crypto, base, price, factor, smallest_increment):
    available_quantity =  get_available_quantity(base)
    buy_quantity = Decimal(available_quantity)* Decimal(factor) / Decimal(price)
    buy_quantity = buy_quantity * get_order_ratio(crypto, base)
    buy_quantity = buy_quantity.quantize(Decimal(smallest_increment))
    return buy_quantity

def create_buy_order(crypto, base, buy_factor):
    order_id = None
    instrument = get_instrument(crypto, base)
    smallest_increment = Decimal(instrument["min_quantity"])
    price = calculate_order_price(crypto, base, SIDE_BUY)
    quantity = calculate_buy_quantity(crypto, base, price, buy_factor, smallest_increment)
    if(quantity >= smallest_increment):
        result = create_order(crypto, base, SIDE_BUY, price, quantity)
        if result and result["result"]:
            order_id = result["result"]["order_id"]
    return order_id

def create_sell_orders(crypto, base, bought_quantity, traded_price, fee_percentage, sell_price_strategy):
    method = "private/create-order-list"
    params = {
        "contingency_type": "LIST",
        "order_list": []
    }
    instrument_name = create_pair(crypto, base)
    instrument = get_instrument(crypto, base)
    smallest_increment = Decimal(instrument["min_quantity"])
    for gain in sell_price_strategy:
        gain_percentage = Decimal(gain)+fee_percentage
        quantity_percentage = Decimal(sell_price_strategy[gain])
        price = traded_price * (1+gain_percentage)
        price = price.quantize(traded_price, rounding = ROUND_UP)
        quantity = bought_quantity * quantity_percentage
        quantity = quantity.quantize(smallest_increment, rounding = ROUND_DOWN)
        param_item = {
            "instrument_name": instrument_name,
            "side": SIDE_SELL,
            "type": "LIMIT",
            "exec_inst": "POST_ONLY",
            "price": float(price),
            "quantity": float(quantity),
            "time_in_force": "GOOD_TILL_CANCEL"
        }
        if(quantity >= smallest_increment):
            params["order_list"].append(param_item)
    print(params)
    result = query(method, params)
    return json.loads(result.text)


def calculate_order_price(crypto, base, order_side):
    """Returns the order price based on the settings and the side of the order (buy vs sell)"""
    #Get the price factor from the settings and choose a rounding: down in case of buy (means buying at a lower price) and up in case of sell (the opposite)
    roundingStrategy = ROUND_DOWN
    current_price = calculate_bid_price(crypto, base)
    if order_side == SIDE_SELL:
        roundingStrategy = ROUND_UP
        current_price = calculate_ask_price(crypto, base)
    #The order price is built as currentPrice * orderFactor, and then rounded down or up with a precision of the minimum price increment possible
    order_price = Decimal(current_price)
    order_price = order_price.quantize(current_price, rounding = roundingStrategy)
    return order_price

def cancel_order(crypto,base,order_id):
    method = "private/cancel-order"
    params = {
        "instrument_name": create_pair(crypto,base),
        "order_id": order_id
    }
    result = query(method,params)
    return json.loads(result.text)

def get_trades(crypto, base, start_time, end_time = None):
    method = "private/get-trades"
    params = {
        "instrument_name": create_pair(crypto,base),
        "start_ts": start_time
    }
    if not end_time:
        end_time = int(time.time())*1000
        params["end_ts"] = end_time
    print(params)
    result = query(method, params)
    json_result = json.loads(result.text)
    print(json_result)
    trades = []
    if json_result and json_result["result"]:
        trades = json_result["result"]["trade_list"]
    return trades

def get_account_summary_text(currency = None):
    result = get_account_summary(currency)
    output = ""
    if result and result["result"]:
        accounts = result["result"]["accounts"]
        for account in accounts:
            if account["balance"] != 0:
                output = output + amount_format(account["balance"]) + " " + account["currency"] + " (" + amount_format(account["available"]) + " available, " + amount_format(account["order"]) + " in order)" +"\n"
    if output == "":
        altText = "active balance"
        if currency:
            altText = currency
        output = "You don't have any " + altText
    return output

def get_current_price_text(crypto, base):
    return "Current " + crypto + " price is " + amount_format(get_current_price(crypto,base)) + " " + base

def get_balance_text(base=None):
    if not base:
        settings = get_json_data(SETTINGS_FILE)
        base = settings[BASE_CURRENCY_KEY]
    return "Current balance is " + amount_format(get_balance(base)) + " " + base

def start_trading_engine():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if not TRADING_ENGINE_ACTIVE:
        TRADING_ENGINE_ACTIVE = 1
        tradingEngineThread = threading.Thread(target = execute_trading_engine)
        tradingEngineThread.start()
        result = "Trading engine correctly started."
    else:
        result =  "Trading engine is already running."
    return result

def stop_trading_engine():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if TRADING_ENGINE_ACTIVE:
        TRADING_ENGINE_ACTIVE = 0
        result = "Trading engine stopped."
    else:
        result = "Trading engine already stopped."
    return result

def get_trading_engine_status_text():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if TRADING_ENGINE_ACTIVE:
        result = "Trading engine is running."
    else:
        result = "Trading engine is not running"
    return result

def execute_trading_engine():
    global TRADING_ENGINE_ACTIVE
    while TRADING_ENGINE_ACTIVE:
        settings = get_json_data(SETTINGS_FILE)
        crypto = settings[CRYPTO_CURRENCY_KEY]
        base = settings[BASE_CURRENCY_KEY]
        order_time_interval = settings[ORDER_TIME_INTERVAL_KEY]
        buy_price_factor = settings[BUY_PRICE_FACTOR_KEY]
        sell_price_strategy = settings[SELL_STRATEGY_KEY]
        current_available_quantity = get_available_quantity(crypto)
        while(get_available_quantity(crypto) == current_available_quantity):
            current_time = int(time.time()*1000)
            order_id = create_buy_order(crypto, base, buy_price_factor)
            time.sleep(order_time_interval)
            if is_buy_open_order(crypto, base):
                cancel_order(crypto, base, order_id)
        bought_quantity = get_available_quantity(crypto) - current_available_quantity
        current_available_quantity = get_available_quantity(crypto)
        trades = get_trades(crypto, base, current_time)
        if trades:
            last_trade = trades[0]
            fee_paid = Decimal(str(last_trade["fee"]))
            traded_price = Decimal(str(last_trade["traded_price"]))
            fee_percentage = fee_paid/bought_quantity
            order_ids = create_sell_orders(crypto, base, bought_quantity, traded_price, fee_percentage, sell_price_strategy)
            #sell the bought quantity, use the traded_price, the fee_percentage and the values in the settings

settings = get_json_data(SETTINGS_FILE)
crypto = settings[CRYPTO_CURRENCY_KEY]
base = settings[BASE_CURRENCY_KEY]
order_time_interval = settings[ORDER_TIME_INTERVAL_KEY]
current_available_quantity = get_available_quantity(crypto)
buy_price_factor = settings[BUY_PRICE_FACTOR_KEY]
sell_price_strategy = settings[SELL_STRATEGY_KEY]
while 1:
    while(get_available_quantity(crypto) == current_available_quantity):
        current_time = int(time.time()*1000)
        order_id = create_buy_order(crypto, base, buy_price_factor)
        print(order_id)
        time.sleep(order_time_interval)
        if is_buy_open_order(crypto, base):
            print("not filled")
            cancel_order(crypto, base, order_id)
        else:
            print("filled")
    bought_quantity = get_available_quantity(crypto) - current_available_quantity
    print(bought_quantity)
    current_available_quantity = get_available_quantity(crypto)
    print(current_available_quantity)
    trades = get_trades(crypto, base, current_time)
    print(trades)
    if trades:
        last_trade = trades[0]
        fee_paid = Decimal(str(last_trade["fee"]))
        print(fee_paid)
        traded_price = Decimal(str(last_trade["traded_price"]))
        print(traded_price)
        fee_percentage = fee_paid/bought_quantity
        print(fee_percentage)
        result = create_sell_orders(crypto, base, bought_quantity, traded_price, fee_percentage, sell_price_strategy)
        print(result)
    settings = get_json_data(SETTINGS_FILE)