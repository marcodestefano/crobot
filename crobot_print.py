from croutils import Decimal, get_settings
from crobot import CRYPTO_CURRENCY_KEY, BASE_CURRENCY_KEY, SIDE_BUY, SIDE_SELL, get_account_summary, get_current_price, get_balance, get_open_orders

MAX_MESSAGE_LENGTH = 4096

def amount_format(value):
    return '{0:f}'.format(Decimal(str(value)))

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

def get_current_price_text(crypto = None, base = None):
    if not crypto:
        settings = get_settings()
        crypto = settings[CRYPTO_CURRENCY_KEY]
    if not base:
        settings = get_settings()
        base = settings[BASE_CURRENCY_KEY]
    return "Current " + crypto + " price is " + amount_format(get_current_price(crypto,base)) + " " + base

def get_balance_text(base=None):
    if not base:
        settings = get_settings()
        base = settings[BASE_CURRENCY_KEY]
    return "Current balance is " + amount_format(get_balance(base)) + " " + base

def get_open_orders_text(crypto = None, base = None):
    if not crypto:
        settings = get_settings()
        crypto = settings[CRYPTO_CURRENCY_KEY]
    if not base:
        settings = get_settings()
        base = settings[BASE_CURRENCY_KEY]
    output = ""
    open_orders = get_open_orders(crypto, base)
    buy_open_orders = {}
    sell_open_orders = {}
    if open_orders and open_orders["result"] and len(open_orders["result"]["order_list"])>0:
        for order in open_orders["result"]["order_list"]:
            actual_orders = {}
            if order["side"] == SIDE_SELL:
                actual_orders = sell_open_orders
            else:
                actual_orders = buy_open_orders
            if not order["price"] in actual_orders:
                actual_orders[order["price"]] = Decimal(0)
            actual_orders[order["price"]] = actual_orders[order["price"]] + Decimal(str(order["quantity"]))
    if len(buy_open_orders) or len(sell_open_orders):
        output = "You have " + str(len(buy_open_orders) + len(sell_open_orders)) + " open orders:\n"
        if len(buy_open_orders):
            output = output + SIDE_BUY + "\n"
        for price, quantity in sorted(buy_open_orders.items()):
            output = output + str(quantity) + " " + crypto + " @ " + str(price) + " " + base + "\n"
        if len(sell_open_orders):
            output = output + SIDE_SELL + "\n"
        for price, quantity in sorted(sell_open_orders.items()):
            output = output + str(quantity) + " " + crypto + " @ " + str(price) + " " + base + "\n"
    return output[:MAX_MESSAGE_LENGTH]
