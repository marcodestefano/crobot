import json
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from crobot import *

BOT_TOKEN_KEY = 'TelegramBotToken'
BOT_USERS_KEY = "Users"

def isAuthorized(update):
    return update.effective_user.username in users

def genericHandler(update, context, function, client=None, settings=None):
    if(isAuthorized(update)):
        if client and settings:
            output = function(client, settings)
        elif client:
            output = function(client)
        else:
            output = function()
        context.bot.send_message(chat_id=update.effective_chat.id, text=output)

def getStartMessage():
    return "Welcome to Belfort! Use /help to retrieve the command list"

def getHelpMessage():
    return "Here's the command list:\n" \
        "/wallet to display your wallets\n" \
        "/orders to display your open orders\n" \
        "/balance to print your current balance\n" \
        "/fills to print your active fills\n" \
        "/sellFills to sell the active fills\n" \
        "/status to check the trading engine status\n" \
        "/startEngine to start the trading engine\n" \
        "/stopEngine to stop the trading engine\n"

def getUnknownMessage():
    return "Sorry, I didn't understand that command."

def start(update, context):
    genericHandler(update,context,getStartMessage)

def displayHelp(update, context):
    genericHandler(update, context, getHelpMessage)

def displayWallet(update, context):
    genericHandler(update, context, get_account_summary_text)

def displayBalance(update, context):
    genericHandler(update, context, get_balance_text)

def status(update, context):
    genericHandler(update, context, get_trading_engine_status_text)

def unknown(update, context):
    genericHandler(update, context, getUnknownMessage)


credentials = get_json_data(SETTINGS_FILE)
tokenData = credentials[BOT_TOKEN_KEY]
users = credentials[BOT_USERS_KEY]
print("Authorized users are: " + str(users))
updater = Updater(token=tokenData)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
displayCommand_handler = CommandHandler('help', displayHelp)
displayWallet_handler = CommandHandler('wallet', displayWallet)
#displayOrders_handler = CommandHandler('orders', displayOrders)
displayBalance_handler = CommandHandler('balance', displayBalance)
#displayFills_handler = CommandHandler('fills', displayFills)
#sellFills_handler = CommandHandler('sellFills', sellFills)
#startEngine_handler = CommandHandler('startEngine', startEngine)
#stopEngine_handler = CommandHandler('stopEngine', stopEngine)
status_handler = CommandHandler('status', status)
unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(displayCommand_handler)
dispatcher.add_handler(displayWallet_handler)
#dispatcher.add_handler(displayOrders_handler)
dispatcher.add_handler(displayBalance_handler)
#dispatcher.add_handler(displayFills_handler)
#dispatcher.add_handler(sellFills_handler)
#dispatcher.add_handler(startEngine_handler)
#dispatcher.add_handler(stopEngine_handler)
dispatcher.add_handler(status_handler)
dispatcher.add_handler(unknown_handler)
updater.start_polling()
print("Bot is active and running")
updater.idle()
