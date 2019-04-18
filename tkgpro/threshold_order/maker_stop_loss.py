from tkgcore.trade_orders import TradeOrder
from tkgcore.action_order import ActionOrder
from tkgcore import core


class MakerStopLossOrder(ActionOrder):
    """
    Start with maker for best amount. Than if price drops above threshold try - recreate order for maker

    if taker price drops above threshold - than set the taker order

    """

    def __init__(self,  symbol, amount: float, price: float, side: str,
                 cancel_threshold: float = 0.000001,
                 maker_price_threshold: float = -0.005,
                 maker_order_max_updates: int = 50,
                 force_taker_updates: int = 500,
                 taker_price_threshold: float = -0.01,
                 taker_order_max_updates: int = 10,
                 threshold_check_after_updates: int = 5):
        """

        :param symbol: pair symbol for order
        :param amount: amount of order in base currency
        :param price: in quote currency
        :param side: "buy" or "sell"
        :param cancel_threshold: cancel current trade order and set new only if the remained amount to fill  is greater than
        this threshold. This is for avoiding the situation of creating new order for less than minimun amount. Usually
        should be minimum order amount/value for the order's pair + commission.
             In ccxt: markets[symbol]["limits"]["amount"]["min"]
        :param force_taker_updates: total number of updates to force the taker state
        :param max_order_updates: order updates before cancelling
        :param taker_price_threshold:  relative difference between the order's price and current taker price. Should be
        negative for changing price in a "bad" way
        :param threshold_check_after_updates: number of order's updates to start requesting ticker and check price
        threshold
        """

        self.maker_price_threshold = maker_price_threshold
        self.maker_order_max_updates = maker_order_max_updates

        self.force_taker_updates = force_taker_updates
        self.taker_price_threshold = taker_price_threshold
        self.taker_order_max_updates = taker_order_max_updates
        self.threshold_check_after_updates = threshold_check_after_updates

        self._total_maker_updates = 0
        """
        total updates in marker state
        """

        super().__init__(symbol, amount, price, side, cancel_threshold, taker_order_max_updates)

    @classmethod
    def create_from_start_amount(cls, symbol, start_currency, start_amount, dest_currency, target_amount,
                                 cancel_threshold: float = 0.000001,
                                 maker_price_threshold: float = -0.005,
                                 maker_order_max_updates: int = 50,
                                 force_taker_updates: int = 500,
                                 taker_price_threshold: float = -0.01,
                                 taker_order_max_updates: int = 10,
                                 threshold_check_after_updates: int = 5):

        """
        :param symbol: pair symbol for order
        :param start_currency: start currency to trade from (available currency)
        :param start_amount: amount of start currency
        :param dest_currency: destination currency to trade to

        :param cancel_threshold: cancel current trade order and set new only if the remained amount to fill  is greater than
        this threshold. This is for avoiding the situation of creating new order for less than minimun amount. Usually
        should be minimum order amount/value for the order's pair + commission.
             In ccxt: markets[symbol]["limits"]["amount"]["min"]
        :param maker_order_max_updates:, :param taker_order_max_updates: max order updates for each separate order in maker/taker phase
        :param maker_price_threshold: ,  :param taker_price_threshold:  relative difference between the order's price and current taker price. Should be
        negative for changing price in a "bad" way
        :param force_taker_updates: total number of updates to force the taker state
        :param threshold_check_after_updates: number of order's updates to start requesting ticker and check price
        threshold
        """

        side = core.get_trade_direction_to_currency(symbol, dest_currency)

        price = core.ticker_price_for_dest_amount(side, start_amount, target_amount)

        order = super().create_from_start_amount(symbol, start_currency, start_amount, dest_currency, price,
                                                 cancel_threshold)  # type: MakerStopLossOrder

        order.maker_price_threshold = maker_price_threshold
        order.maker_order_max_updates = maker_order_max_updates

        order.taker_price_threshold = taker_price_threshold
        order.taker_order_max_updates = taker_order_max_updates
        order.threshold_check_after_updates = threshold_check_after_updates

        order.force_taker_updates = force_taker_updates

        return order

    def _init(self):
        super()._init()

        self.status = "open"
        self.state = "maker"
        self.order_command = "new"
        self.active_trade_order.supplementary.update({"parent_action_order": {"state": self.state}})

    def _on_open_order(self, active_trade_order: TradeOrder, market_data=None):

        order_command = "hold tickers {symbol}".format(symbol=self.symbol)

        # maker state
        if self.state == "maker":

            self._total_maker_updates += 1

            # let's start requesting the tickers
            order_command = "hold tickers {symbol}".format(symbol=self.symbol)

            # cancel if reach force_taker_updates
            if self._total_maker_updates >= self.force_taker_updates \
                    and self.amount - self.filled > self.cancel_threshold:

                self.tags.append("#force_taker_max_maker_updates")
                self.state = "taker"
                return "cancel tickers {symbol}".format(symbol=self.symbol)

            # check if need to re-open maker order becaus of reaching single  maker order updates limit
            if active_trade_order.update_requests_count >= self.maker_order_max_updates \
                    and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:
                return "cancel tickers {symbol}".format(symbol=self.symbol)

            order_command = "hold tickers {symbol}".format(symbol=self.symbol)

            current_taker_price, current_maker_price = 0, 0

            # let's check if taker price below the thresholds
            # current_taker_price, current_taker_price = 0, 0

            # if there is no market data - just return default command
            if market_data is not None:
                try:
                    ticker_info = core.get_symbol_order_price_from_tickers(self.start_currency,
                                                                           self.dest_currency,
                                                                           {self.symbol: market_data[0]})
                    current_taker_price = ticker_info["price"]
                    current_maker_price = ticker_info["maker_price"]

                except Exception as e:
                    order_command = "hold tickers {symbol}".format(symbol=self.symbol)
                    return order_command

            # check taker price for both states
            if current_taker_price > 0:
                relative_price_diff = core.relative_target_price_difference(self.side, self.price,
                                                                            current_taker_price)

                if relative_price_diff is not None and relative_price_diff <= self.taker_price_threshold:
                    order_command = "cancel tickers {symbol}".format(symbol=self.symbol)
                    self.state = "taker"

                    if "#below_threshold_taker" not in self.tags:
                        self.tags.append("#below_threshold_taker_price")
                    return order_command

            # check maker price
            if current_maker_price > 0:
                relative_price_diff = core.relative_target_price_difference(self.side, self.price,
                                                                            current_maker_price)

                if relative_price_diff is not None and relative_price_diff <= self.maker_price_threshold:
                    order_command = "cancel tickers {symbol}".format(symbol=self.active_trade_order.symbol)
                    self.state = "maker"

                    if "#below_threshold_maker" not in self.tags:
                        self.tags.append("#below_threshold_maker")
                    return order_command

        if self.state == "taker":

            # reset the taker order
            if active_trade_order.update_requests_count >= self.taker_order_max_updates \
                    and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:

                self.stare = "taker"
                return "cancel tickers {symbol}".format(symbol=self.symbol)

        return order_command

    def _on_closed_order(self, active_trade_order: TradeOrder, market_data=None):

        self._close_active_order()

        self.order_command = "hold tickers {symbol}".format(symbol=self.symbol)

        if self.filled_start_amount >= self.start_amount * 0.99999:  # close order if filled amount is OK
            self.order_command = ""
            self.close_order()  # we just need to close ActionOrder, the trade order was closed above
            return self.order_command

        # check if we have new prioe in market data
        if market_data is None:
            return self.order_command

        ticker_info = core.get_symbol_order_price_from_tickers(self.start_currency,
                                                               self.dest_currency,
                                                               {self.symbol: market_data[0]})
        current_taker_price = ticker_info["price"]
        current_maker_price = ticker_info["maker_price"]

        if self.state == "maker":
            self.active_trade_order = self._create_next_trade_order_for_remained_amount(current_maker_price)
            self.order_command = "new tickers {symbol}".format(symbol=self.symbol)
            return self.order_command

        if self.state == "taker":
            self.active_trade_order = self._create_next_trade_order_for_remained_amount(current_taker_price)
            self.order_command = "new tickers {symbol}".format(symbol=self.symbol)
            return self.order_command

        return self.order_command

