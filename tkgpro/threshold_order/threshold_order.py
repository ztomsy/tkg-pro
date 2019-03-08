import tkgcore
from tkgcore import core
from tkgcore import errors
from tkgcore import TradeOrder
from tkgcore import ActionOrder
from tkgcore import RecoveryOrder
import time
import uuid
from tkgcore import ccxtExchangeWrapper


class ThresholdRecoveryOrder(RecoveryOrder):

    def __init__(self, symbol, start_currency: str, start_amount: float, dest_currency: str,
                 dest_amount: float = 0.0, taker_price_threshold:float = -0.01,
                 fee: float=0.0, cancel_threshold: float=0.000001, max_best_amount_order_updates: int=50,
                 max_order_updates: int=10):
        """
        ThresholdRecovery Order is aimed to be filled for the setted dest amount and if fails fills
        on best market price. If the price will drop (or raise) belowe the threshold - order will be filled via taker
        market price.

        Workflow of ThresholdRecoveryOrder:
        - create limit order with the price in accordance to received best dest amount (best_amount state)
        - while in best_amount state order being checking the price from ticker and if if falls below the realative
        threshold, proceed to fill the order on market price
        - run a series of consecutive limit orders on ticker price (taker)

        :param symbol: pair symbol for order
        :param start_currency: start currency to trade from (available currency)
        :param start_amount: amount of start currency
        :param dest_currency: destination currency to trade to
        :param dest_amount: amount of dest currency
        :param taker_price_threshold: relative difference between the best_amount price and current price. Should be
        negative for changing price in a "bad" way
        :param fee: exchange fee for order (not used)
        :param cancel_threshold: cancel current trade order and set new only if the remained amount to fill  is greater than
        this threshold. This is for avoiding the situation of creating new order for less than minimun amount. Usually
        should be minimum order amount/value for the order's pair + commission.
             In ccxt: markets[symbol]["limits"]["amount"]["min"]
        :param max_best_amount_order_updates: number of best amount trade order updates before cancelling
        :param max_order_updates:  max order updates for market price trade orders

        """
        self.id = str(uuid.uuid4())
        self.timestamp = time.time()  # timestamp of object creation
        self.timestamp_close = float()

        self.symbol = symbol
        self.start_currency = start_currency
        self.start_amount = start_amount
        self.dest_currency = dest_currency
        self.fee = fee
        self.cancel_threshold = cancel_threshold  #
        self.best_dest_amount = dest_amount
        self.best_price = 0.0
        self.price = 0.0
        self.taker_price_threshold = taker_price_threshold

        self.status = "new"  # new, open, closed
        self.state = "best_amount"  # "market_price" for reporting purposes

        self.filled_dest_amount = 0.0
        self.filled_start_amount = 0.0
        self.filled_price = 0.0

        self.filled = 0.0  # filled amount of base currency
        self.amount = 0.0  # total expected amount of to be filled base currency

        self.max_best_amount_orders_updates = max_best_amount_order_updates  # max order updates for best amount
        self.max_order_updates = max_order_updates  # max amount of order updates for market price orders

        self.order_command = None  # None, new, cancel

        if symbol is not None:
            self.side = core.get_trade_direction_to_currency(symbol, self.dest_currency)
            if self.side == "buy":
                self.amount = self.best_dest_amount
            else:
                self.amount = self.start_amount

        self.active_trade_order = None  # .. TradeOrder
        self.orders_history = list()

        self.tags = list()
        self.market_data = dict()  # market data dict: {symbol : {price :{"buy": <ask_price>, "sell": <sell_price>}}

        self._prev_filled_dest_amount = 0.0   # filled amounts on previous orders
        self._prev_filled_start_amount = 0.0  # filled amountsbot, on previous orders
        self._prev_filled = 0.0               # filled amounts on previous orders

        self._prev_price_diff = 0.0

        self._init_best_amount()

    def _init_best_amount(self):
        price = self._get_recovery_price_for_best_dest_amount()

        self.status = "open"
        self.state = "best_amount"
        self.best_price = price

        self.active_trade_order = self._create_recovery_order(price, self.state)
        self.order_command = "new tickers {}".format(self.symbol)  # will start requesting the tickers from the creation

    def update_from_exchange(self, resp, market_data=None):
        """
        :param resp:
        :param market_data: some market data (price, orderbook?) for new tradeOrder
        :return: updates the self.order_command

        """
        self.active_trade_order.update_order_from_exchange_resp(resp)

        self.filled_dest_amount = self._prev_filled_dest_amount + self.active_trade_order.filled_dest_amount
        self.filled_start_amount = self._prev_filled_start_amount + self.active_trade_order.filled_start_amount

        if self.filled_dest_amount != 0 and self.filled_start_amount != 0:
            self.filled_price = self.filled_start_amount / self.filled_dest_amount if self.side == "buy" else \
                self.filled_dest_amount / self.filled_start_amount

        self.filled = self._prev_filled + self.active_trade_order.filled

        current_state_max_order_updates = self.max_order_updates

        if self.state == "best_amount" and self.active_trade_order.status == "open":

            current_state_max_order_updates = self.max_best_amount_orders_updates
            self.order_command = "hold tickers {symbol}".format(symbol=self.symbol)

            try:

                current_taker_price = core.get_symbol_order_price_from_tickers(self.start_currency, self.dest_currency,
                                                                               {self.symbol: market_data[0]})["price"]
                if current_taker_price > 0:
                    price_diff = core.relative_target_price_difference(self.side, self.best_price, current_taker_price)
                    self._prev_price_diff = price_diff

                    if price_diff is not None and price_diff <= self.taker_price_threshold:
                        self.order_command = "cancel tickers {symbol}".format(symbol=self.active_trade_order.symbol)
                        if "#below_threshold" not in self.tags:
                            self.tags.append("#below_threshold")

                        return self.order_command

            except Exception as e:
                self.order_command = "hold tickers {symbol}".format(symbol=self.symbol)

        if self.state == "market_price":
            current_state_max_order_updates = self.max_order_updates
            self.order_command = "hold tickers {symbol}".format(symbol=self.active_trade_order.symbol)

        if self.active_trade_order.status == "open":

            if self.active_trade_order.update_requests_count >= current_state_max_order_updates \
                    and self.active_trade_order.amount - self.active_trade_order.filled > self.cancel_threshold:

                # add ticker request command to order manager
                self.order_command = "cancel tickers {symbol}".format(symbol=self.active_trade_order.symbol)

            return self.order_command

        if self.active_trade_order.status == "closed" or self.active_trade_order.status == "canceled":

            if self.filled_start_amount >= self.start_amount*0.99999:  # close order if filled amount is OK
                self.order_command = ""
                self._close_active_order()
                self.close_order()
                return self.order_command

            self.state = "market_price"  # else set new order status
            if market_data is not None and market_data[0] is not None:
                self._close_active_order()

                ticker = market_data[0]

                new_price = core.get_symbol_order_price_from_tickers(self.start_currency, self.dest_currency,
                                                                     {self.symbol: ticker})["price"]

                self.active_trade_order = self._create_recovery_order(new_price, self.state)
                self.order_command = "new"
            else:
                # if we did not received ticker - so just re request the ticker
                self.order_command = "hold tickers {symbol}".format(symbol=self.active_trade_order.symbol)

                # print("New price not set... Hodling..")
                # raise errors.OrderError("New price not set")

            return self.order_command


