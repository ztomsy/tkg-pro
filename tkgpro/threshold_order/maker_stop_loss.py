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
                 maker_price_threshold: float = 0.005,
                 maker_order_max_updates: int = 50,
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
        :param max_order_updates: order updates before cancelling
        :param taker_price_threshold:  relative difference between the order's price and current taker price. Should be
        negative for changing price in a "bad" way
        :param threshold_check_after_updates: number of order's updates to start requesting ticker and check price
        threshold
        """

        self.maker_price_threshold = maker_price_threshold
        self.maker_order_max_updates = maker_order_max_updates

        self.taker_price_threshold = taker_price_threshold
        self.taker_order_max_updates = taker_order_max_updates
        self.threshold_check_after_updates = threshold_check_after_updates

        super().__init__(symbol, amount, price, side, cancel_threshold, taker_order_max_updates)

    @classmethod
    def create_from_start_amount(cls, symbol, start_currency, start_amount, dest_currency, target_amount,
                                 cancel_threshold: float = 0.000001,
                                 maker_price_threshold: float = 0.005,
                                 maker_order_max_updates: int = 50,
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
        :param threshold_check_after_updates: number of order's updates to start requesting ticker and check price
        threshold
        """

        side = core.get_trade_direction_to_currency(symbol, dest_currency)

        price = core.ticker_price_for_dest_amount(side, start_amount, target_amount)

        order = super().create_from_start_amount(symbol, start_currency, start_amount, dest_currency, price,
                                                 cancel_threshold)

        order.maker_price_threshold = maker_price_threshold
        order.maker_order_max_updates = maker_order_max_updates

        order.taker_price_threshold = taker_price_threshold
        order.taker_order_max_updates = taker_order_max_updates
        order.threshold_check_after_updates = threshold_check_after_updates

        return order

    def _init(self):
        super()._init()

        self.status = "open"
        self.state = "maker"
        self.order_command = "new"
        self.active_trade_order.supplementary.update({"parent_action_order": {"state": self.state}})

    def _on_open_order(self, active_trade_order: TradeOrder, market_data=None):

        # cancel if have reached the maximum number of updates
        order_command = "hold"

        # maker state
        if self.state == "maker":

            # let's start requesting the tickers
            order_command = "hold tickers {symbol}".format(symbol=self.symbol)

            # cancel if reach maker_order_max_updates
            if active_trade_order.update_requests_count >= self.maker_order_max_updates \
                    and active_trade_order.amount - active_trade_order.filled > self.cancel_threshold:
                return "cancel"

            # if there is no market data - just return default command
            if market_data is None:
                return order_command

            order_command = "hold tickers {symbol}".format(symbol=self.symbol)

            # than if market data is present - let's check if it's below or above the thresholds
            try:
                ticker_info = core.get_symbol_order_price_from_tickers(self.start_currency,
                                                                                  self.dest_currency,
                                                                                  {self.symbol: market_data[0]})
                current_taker_price = ticker_info["price"]
                current_maker_price = ticker_info["maker_price"]

                # check taker price
                if current_taker_price > 0:
                    relative_price_diff = core.relative_target_price_difference(self.side, self.price, current_taker_price)

                    if relative_price_diff is not None and relative_price_diff <= self.taker_price_threshold:
                        order_command = "cancel"
                        self.status = "taker"

                        if "#below_threshold_taker" not in self.tags:
                            self.tags.append("#below_threshold_taker_price")
                        return order_command

                # check maker price
                if current_maker_price > 0:
                    relative_price_diff = core.relative_target_price_difference(self.side, self.price, current_maker_price)

                    if relative_price_diff is not None and relative_price_diff <= self.taker_maker_threshold:
                        order_command = "cancel"
                        self.status = "maker"

                        if "#below_threshold_maker" not in self.tags:
                            self.tags.append("#below_threshold_maker")
                        return order_command

            except Exception as e:
                order_command = "hold tickers {symbol}".format(symbol=self.symbol)

        return order_command
