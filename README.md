# crobot

A python tool to trade cryptocurrencies on crypto.com/exchange

## How to use crobot:

### Before starting

#### Install dependencies
- python-telegram-bot (pip install python-telegram-bot)

crobot requires at least Python 3.0 version. It has been tested with Python 3.7

#### Configure the tool with your crypto.com/exchange API key
1. You need to rename the file settings.json.sample into settings.json and put your own crypto.com/exchange APIKey and APISecret. To know how to create an API key, please follow the official guide https://exchange-docs.crypto.com/spot/index.html#generating-the-api-key
2. (Optional) You can also activate and control crobot via a telegram bot. To do that, you need to put your own TelegramBotToken into settings.json file. To know how to define a bot, please follow the official guide here: https://core.telegram.org/bots#6-botfather
3. (Optional, but recommended if you are using the telegram bot) To limit users that can access the otherwise publicly available bot, you need to specify the authorized telegram usernames into settings.json file

#### Understand settings.json file

File settings.json contains settings used in running the engine, that can be customized. The following are the parameters that can be changed to customize crobot trading engine behavior:


- BASE_CURRENCY: the base currency to use (usually a stablecoin - default is )
- CRYPTO_CURRENCY: the crypto currency to trade
- ORDER_TIME_INTERVAL: Time interval in seconds between two new buy orders
- BUY_AMOUNT_FACTOR: Ratio of the available base currency to use when placing buying orders
- SELL_STRATEGY: Split of sell orders to place on the bought crypto, represented as a table with key the desired percentage gain (net of paid fees) and value the ratio of total available to be sold at that gain. As an example, the following sell strategy:
{
	"0.05": 0.3,
        "0.15": 0.3,
        "0.20": 0.3,
        "0.25": 0.1
}

means that crobot is going to sell 30% of the bought crypto at a price to get a gain of 5%, 30% to get a gain of 15%, 30% to get a gain of 20% and 10% to get a gain of 25%.

### Running the trading engine

There are two main ways to run the trading engine: calling the start_trading_engine_function from crobot.py in your script or by using crobotgram.py. The former is intended for extension, usage and control as a standard python script, the latter for usage via telegram bot. To start crobot with the telegram option just run: python crobotgram.py


#### Features

If you are using the crobotgram script, you'll be prompted with these options:

```
Welcome to crobot!

/wallet to display your wallets
/orders to display your open orders
/balance to print your current balance
/status to check the trading engine status
/startEngine to start the trading engine
/stopEngine to stop the trading engine
```


These features behave as follows:
1. Display wallet: crobot shows the amount of cryptos in the crypto.com exchange wallet linked to your API Key
2. Display orders: crobot shows the currently open orders
3. Print balance: crobot shows the overall value of your wallet converted in your selected base currency
4. Check status: crobot shows the status of the trading engine (i.e. if it is currently running or not)
5. Start trading engine: crobot starts the trading engine with the parameters defined in settings.json file
6. Stop trading engine: crobot stops the trading engine