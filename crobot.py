from cgitb import small
import threading
import traceback
from decimal import ROUND_DOWN, ROUND_UP
from croutils import json, time, Decimal, query, public_query, create_pair, get_ratio, get_settings

TRADING_ENGINE_ACTIVE = 0
CRYPTO_CURRENCY_KEY = "CRYPTO_CURRENCY"
BASE_CURRENCY_KEY = "BASE_CURRENCY"
ORDER_TIME_INTERVAL_KEY = "ORDER_TIME_INTERVAL"
BUY_AMOUNT_FACTOR_KEY = "BUY_AMOUNT_FACTOR"
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
    result = public_query(method, params)
    return json.loads(result.text)

def get_order_history(crypto, base):
    method = "private/get-order-history"
    params = {
        "instrument_name": create_pair(crypto, base)
    }
    result = query(method, params)
    return json.loads(result.text)

def get_open_orders(crypto, base):
    method = "private/get-open-orders"
    params = {
        "instrument_name": create_pair(crypto, base),
        "page_size": 200
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
    result = public_query(method)
    json_result = json.loads(result.text)
    instrument_result = None
    if (json_result and json_result["result"]):
        for instrument in json_result["result"]["instruments"]:
            if instrument["quote_currency"] == base and instrument["base_currency"] == crypto:
                instrument_result = instrument
    return instrument_result

def get_balance(base):
    total_value = Decimal(0)
    summary = get_account_summary()
    if summary and summary["result"]:
        accounts = summary["result"]["accounts"]
        for account in accounts:
            if account["balance"] != 0:
                if account["currency"] == base:
                    total_value = total_value + Decimal(str(account["balance"]))
                else:
                    total_value = total_value + Decimal(str(account["balance"]))*get_current_price(account["currency"],base)
    return total_value

def get_current_price(crypto,base):
    result = get_ticker(crypto, base)
    current_price = None
    if (result and result["result"]):
        current_price = result["result"]["data"]["a"]
    return Decimal(str(current_price))

def get_bid_price(crypto, base):
    result = get_ticker(crypto, base)
    bid_price = Decimal('-Inf')
    if (result and result["result"]):
        bid_price = Decimal(str(result["result"]["data"]["b"]))
    return bid_price

def get_ask_price(crypto, base):
    result = get_ticker(crypto, base)
    ask_price = Decimal('Inf')
    if (result and result["result"]):
        ask_price = Decimal(str(result["result"]["data"]["k"]))
    return ask_price

def get_product_min_max_value(crypto, base, interval):
    method = "public/get-candlestick"
    params = {
        "instrument_name": create_pair(crypto, base),
        "timeframe": INTERVAL_1M
    }
    result = public_query(method, params)
    json_result = json.loads(result.text)
    min_max = {}
    #At the beginning, the min is set to Infinity and the max to -Infinity
    min_max[PRODUCT_MIN_VALUE] = Decimal('Inf')
    min_max[PRODUCT_MAX_VALUE] = Decimal('-Inf')
    current_time = time.time()
    #Max past is the oldest data to be taken into account, based on the interval choosen (e.g. 1 month in the past, 6 month in the past)
    max_past = current_time - interval
    max_past = max_past * 1000
    if json_result and json_result["result"]:
        for candle in json_result["result"]["data"]:
            #update the min/max only if max_past is more in the past than current candle timestamp
            if max_past < candle["t"]:
                if min_max[PRODUCT_MIN_VALUE] > candle["l"]:
                    min_max[PRODUCT_MIN_VALUE] = candle["l"]
                if min_max[PRODUCT_MAX_VALUE] < candle["h"]:
                    min_max[PRODUCT_MAX_VALUE] = candle["h"]
    return min_max

def get_order_ratio(crypto, base):
    #calculate the min and max values for these period of time: 1month, 1quarter, 1semester, 1year
    year_min_max = get_product_min_max_value(crypto, base, TIME_INTERVAL_YEAR)
    semester_min_max = get_product_min_max_value(crypto, base, TIME_INTERVAL_SEMESTER)
    quarter_min_max = get_product_min_max_value(crypto, base, TIME_INTERVAL_QUARTER)
    month_min_max = get_product_min_max_value(crypto, base, TIME_INTERVAL_MONTH)
    #get the current price of the crypto
    currentValue = get_current_price(crypto, base)
    #calculate the ratio for each period, to ensure we're not buying too much when the price is high (depend on the max and mins of the different time ranges)
    ratio_1y = RATIO_1Y * get_ratio(currentValue, year_min_max[PRODUCT_MIN_VALUE], year_min_max[PRODUCT_MAX_VALUE])
    ratio_6m = RATIO_6M * get_ratio(currentValue, semester_min_max[PRODUCT_MIN_VALUE], semester_min_max[PRODUCT_MAX_VALUE])
    ratio_3m = RATIO_3M * get_ratio(currentValue, quarter_min_max[PRODUCT_MIN_VALUE], quarter_min_max[PRODUCT_MAX_VALUE])
    ratio_1m = RATIO_1M * get_ratio(currentValue, month_min_max[PRODUCT_MIN_VALUE], month_min_max[PRODUCT_MAX_VALUE])
    return ratio_1y + ratio_6m + ratio_3m + ratio_1m

def calculate_buy_quantity(crypto, base, price, factor, smallest_increment):
    available_quantity =  get_available_quantity(base)
    buy_quantity = Decimal(available_quantity)* Decimal(factor) / Decimal(price)
    buy_quantity = buy_quantity * get_order_ratio(crypto, base)
    buy_quantity = buy_quantity.quantize(Decimal(smallest_increment))
    return buy_quantity

def create_buy_order(crypto, base, buy_factor):
    order_id = None
    method = "private/create-order"
    params = {
        "instrument_name": create_pair(crypto,base),
        "side": SIDE_BUY,
        "type": "LIMIT",
        "exec_inst": "POST_ONLY",
        "time_in_force": "GOOD_TILL_CANCEL"
        }
    instrument = get_instrument(crypto, base)
    #Get the smallest amount that could be bought (also to know the decimals of the amount)
    smallest_increment = Decimal(instrument["min_quantity"])
    #Calculate the order price for the currency pair
    price = get_bid_price(crypto, base)
    #Calculate the quantity that can be bought for the pair, considering the buy_factor and the minimum amount
    quantity = calculate_buy_quantity(crypto, base, price, buy_factor, smallest_increment)
    #If the quantity is more than the minimum, the order can be placed
    text = "Quantity " + str(quantity) + " is lower than smallest increment " + str(smallest_increment)
    if(quantity >= smallest_increment):
        text = "Placing buy order with price " + str(price) + " and quantity " + str(quantity)
        params["price"] = float(price)
        params["quantity"] = float(quantity)
        result = query(method, params)
        json_result = json.loads(result.text)
        if json_result and json_result["result"]:
            order_id = json_result["result"]["order_id"]
    print(time.strftime("%Y-%m-%d %H:%M:%S") + " " + text)
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
    total_selling_quantity = Decimal(0)
    # Get the pairs <gain_percentage, quantity_percentage> from settings, and create sell orders for all of them
    for gain in sell_price_strategy:
        #Adding to the gain the fee_percentage paid when buying
        gain_percentage = Decimal(gain)+fee_percentage
        quantity_percentage = Decimal(sell_price_strategy[gain])
        #Sell price is going to be the traded price reevaulated based on the gain_percentage
        price = traded_price * (1+gain_percentage)
        price = price.quantize(traded_price, rounding = ROUND_UP)
        #The quantity to be sold is the full quantity percentage - the fee_percentage that was paid
        quantity = bought_quantity * (quantity_percentage - fee_percentage)
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
            print(time.strftime("%Y-%m-%d %H:%M:%S") + " Selling " + str(quantity) + " " + crypto + " @ " + str(price) + " " + base)
            total_selling_quantity = total_selling_quantity + quantity
    result = query(method, params)
    json_result = json.loads(result.text)
    #There might be remaining quantity that can be sold: in this case, let's sell the "dust" at a price to cover just the fee_percentages
    price = traded_price * (1+fee_percentage+fee_percentage)
    current_ask_price = get_ask_price(crypto, base)
    #If the price is lower than the current ask price, let's sell at the ask price for a better gain
    if price < current_ask_price:
        price = current_ask_price
    price = price.quantize(traded_price, rounding = ROUND_UP)
    remaining_available_quantity = bought_quantity - total_selling_quantity - bought_quantity*fee_percentage*2
    remaining_available_quantity = remaining_available_quantity.quantize(smallest_increment, rounding = ROUND_DOWN)
    if remaining_available_quantity > smallest_increment:
        method = "private/create-order"
        params = {
            "instrument_name": instrument_name,
            "side": SIDE_SELL,
            "type": "LIMIT",
            "exec_inst": "POST_ONLY",
            "price": float(price),
            "quantity": float(remaining_available_quantity),
            "time_in_force": "GOOD_TILL_CANCEL"
        }
        print(time.strftime("%Y-%m-%d %H:%M:%S") + " Selling " + str(remaining_available_quantity) + " " + crypto + " dust @ " + str(price) + " " + base)
    result = query(method, params)
    json_result.update(json.loads(result.text))
    return json_result

def cancel_order(crypto,base,order_id):
    method = "private/cancel-order"
    params = {
        "instrument_name": create_pair(crypto,base),
        "order_id": order_id
    }
    print(time.strftime("%Y-%m-%d %H:%M:%S") + " Canceling order " + str(order_id))
    result = query(method,params)
    return json.loads(result.text)

def get_trades(crypto, base, start_time, end_time = None):
    method = "private/get-trades"
    params = {
        "instrument_name": create_pair(crypto,base),
        "start_ts": start_time
    }
    #If end_time is not provided, let's set it as current time
    if not end_time:
        end_time = int(time.time())*1000
        params["end_ts"] = end_time
    result = query(method, params)
    json_result = json.loads(result.text)
    trades = []
    if json_result and json_result["result"]:
        trades = json_result["result"]["trade_list"]
    return trades

def get_buy_trades(crypto, base, current_time):
    buy_trades = []
    all_trades = get_trades(crypto, base, current_time)
    if all_trades:
        for trade in all_trades:
            if(trade["side"] == SIDE_BUY):
                buy_trades.append(trade)
    return buy_trades

def start_trading_engine():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if not TRADING_ENGINE_ACTIVE:
        TRADING_ENGINE_ACTIVE = 1
        tradingEngineThread = threading.Thread(target = execute_trading_engine)
        tradingEngineThread.start()
        result = "Trading engine correctly started"
    else:
        result =  "Trading engine is already running"
    print(result)
    return result

def stop_trading_engine():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if TRADING_ENGINE_ACTIVE:
        TRADING_ENGINE_ACTIVE = 0
        result = "Trading engine stopped"
    else:
        result = "Trading engine already stopped"
    print(result)
    return result

def get_trading_engine_status_text():
    result = ""
    global TRADING_ENGINE_ACTIVE
    if TRADING_ENGINE_ACTIVE:
        result = "Trading engine is running"
    else:
        result = "Trading engine is not running"
    return result

def execute_trading_engine():
    try:
        global TRADING_ENGINE_ACTIVE
        while TRADING_ENGINE_ACTIVE:
            #get setting file and its content: crypto and base currency to use, the time interval between the placement of two buy orders, the buy amount factor and the selling strategy.
            settings = get_settings()
            crypto = settings[CRYPTO_CURRENCY_KEY]
            base = settings[BASE_CURRENCY_KEY]
            order_time_interval = settings[ORDER_TIME_INTERVAL_KEY]
            buy_amount_factor = settings[BUY_AMOUNT_FACTOR_KEY]
            sell_price_strategy = settings[SELL_STRATEGY_KEY]
            current_available_quantity = get_available_quantity(crypto)
            # if available quantity <= current_available_quantity means there's no new crypto available to be sold, so a new buy order needs to be placed
            while(get_available_quantity(crypto) <= current_available_quantity):
                #get current time to use later to filter open orders
                current_time = int(time.time()*1000)
                # create a buy order on selected crypto/base pair, and get its id
                order_id = create_buy_order(crypto, base, buy_amount_factor)
                #wait the time interval passes before attempting another order
                time.sleep(order_time_interval/2)
                #if the order is still ACTIVE, let's cancel it and check if at least partially filled (checking on the while loop, if there's new available quantity)
                if order_id and is_buy_open_order(crypto, base):
                    cancel_order(crypto, base, order_id)
                    time.sleep(1)
                elif order_id:
                    print(time.strftime("%Y-%m-%d %H:%M:%S") + " Order " + str(order_id) + " filled")
            #get buy trades since time snapshot got earlier 
            trades = get_buy_trades(crypto, base, current_time)
            if trades:
                fee_paid = Decimal(0)
                bought_quantity = Decimal(0)
                traded_price = Decimal(0)
                # getting all trades: they will all have the same traded price, let's sum quantity and fees to be able to sell
                for trade in trades:
                    if traded_price == 0:
                        traded_price = Decimal(str(trade["traded_price"]))
                    fee_paid = fee_paid + Decimal(str(trade["fee"]))
                    bought_quantity = bought_quantity + Decimal(str(trade["traded_quantity"]))
                fee_percentage = fee_paid/bought_quantity
                #sell the bought quantity, use the traded_price, the fee_percentage and the values in the settings
                create_sell_orders(crypto, base, bought_quantity, traded_price, fee_percentage, sell_price_strategy)
                time.sleep(order_time_interval/2)
    except Exception:
        stop_trading_engine()
        print(time.strftime("%Y-%m-%d %H:%M:%S") + " Error in the execution of the engine: " + str(traceback.print_exc()))
        start_trading_engine()
    return