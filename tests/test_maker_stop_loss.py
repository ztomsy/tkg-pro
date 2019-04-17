# -*- coding: utf-8 -*-
from .context import tkgpro
from tkgpro import MakerStopLossOrder
from tkgcore import core, ccxtExchangeWrapper, ActionOrderManager

import unittest


class MakerStopLossOrderTestSuite(unittest.TestCase):

    def test_create(self):
        
        o = MakerStopLossOrder(
            symbol="ETH/BTC",
            amount=1,
            price=0.01,
            side="sell",
            cancel_threshold=0.001,
            maker_price_threshold=-0.003,
            maker_order_max_updates=60,
            force_taker_updates=1000,
            taker_price_threshold=-0.02,
            taker_order_max_updates=20,
            threshold_check_after_updates=6
        )
        
        self.assertEqual(o.symbol, "ETH/BTC")
        self.assertEqual(o.amount, 1)
        self.assertEqual(o.price,  0.01)
        self.assertEqual(o.side, "sell")
        self.assertEqual(o.cancel_threshold , 0.001)
        self.assertEqual(o.maker_price_threshold, -0.003)
        self.assertEqual(o.maker_order_max_updates, 60)
        self.assertEqual(o.taker_price_threshold, -0.02)
        self.assertEqual(o.taker_order_max_updates, 20)
        self.assertEqual(o.threshold_check_after_updates, 6)

        self.assertEqual(1000, o.force_taker_updates)

        self.assertEqual("maker", o.state)
        self.assertEqual("open", o.status)

        self.assertEqual("new", o.order_command)

    def test_create_from_start_amount(self):

        o = MakerStopLossOrder.create_from_start_amount(
            symbol="ETH/BTC",
            start_currency="ETH",
            start_amount=1,
            dest_currency="BTC",
            target_amount=0.01,
            cancel_threshold=0.001,
            maker_price_threshold=-0.003,
            maker_order_max_updates=60,
            force_taker_updates=1000,
            taker_price_threshold=-0.02,
            taker_order_max_updates=20,
            threshold_check_after_updates=6
        )

        self.assertEqual(o.symbol, "ETH/BTC")
        self.assertEqual(o.amount, 1)
        self.assertEqual(o.price,  0.01)
        self.assertEqual(o.side, "sell")
        self.assertEqual(o.cancel_threshold , 0.001)
        self.assertEqual(o.maker_price_threshold, -0.003)
        self.assertEqual(o.maker_order_max_updates, 60)
        self.assertEqual(o.taker_price_threshold, -0.02)
        self.assertEqual(o.taker_order_max_updates, 20)
        self.assertEqual(o.threshold_check_after_updates, 6)

        self.assertEqual(1000, o.force_taker_updates)

        self.assertEqual("maker", o.state)
        self.assertEqual("open", o.status)

        self.assertEqual("new", o.order_command)

    def test_relative_maker_price_dff(self):
        """
        check how relative price difference works
        """

        side = "buy"
        order_price = 1
        current_maker_price = 1.1

        relative_price_diff = core.relative_target_price_difference(side, order_price, current_maker_price)

        self.assertAlmostEqual(relative_price_diff, -0.1, 8)

        side = "buy"
        order_price = 1
        current_maker_price = 1.01
        relative_price_diff = core.relative_target_price_difference(side, order_price, current_maker_price)
        self.assertAlmostEqual(relative_price_diff, -0.01, 8)

        side = "buy"
        order_price = 1
        current_maker_price = 1
        relative_price_diff = core.relative_target_price_difference(side, order_price, current_maker_price)
        self.assertAlmostEqual(relative_price_diff, 0, 8)

        side = "buy"
        order_price = 1
        current_maker_price = 0.9
        relative_price_diff = core.relative_target_price_difference(side, order_price, current_maker_price)
        self.assertAlmostEqual(relative_price_diff, 0.1, 8)

        # sell
        side = "sell"
        order_price = 1
        current_maker_price = 1
        relative_price_diff = core.relative_target_price_difference(side, order_price, current_maker_price)
        self.assertAlmostEqual(relative_price_diff, 0, 8)

        side = "sell"
        order_price = 1
        current_maker_price = 0.9
        relative_price_diff = core.relative_target_price_difference(side, order_price, current_maker_price)
        self.assertAlmostEqual(relative_price_diff, -0.1, 8)

        side = "sell"
        order_price = 1
        current_maker_price = 0.99
        relative_price_diff = core.relative_target_price_difference(side, order_price, current_maker_price)
        self.assertAlmostEqual(relative_price_diff, -0.01, 8)

    def test_multi_maker_fill_is_good(self):
        ex = ccxtExchangeWrapper.load_from_id("binancae") # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers_maker.csv")

        om = ActionOrderManager(ex)
        om.offline_order_updates = 10  # number of updates to fill order from offline data

        order = MakerStopLossOrder.create_from_start_amount(
            symbol="BTC/USDT",
            start_currency="BTC",
            start_amount=1,
            dest_currency="USDT",
            target_amount=1,
            cancel_threshold=0.001,
            maker_price_threshold=-0.01,
            maker_order_max_updates=60,
            taker_price_threshold=-0.02,
            taker_order_max_updates=20,
            threshold_check_after_updates=6
        )
        om.add_order(order)
        om.proceed_orders()  # update 1: order creation

        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.99}}}

        om.data_for_orders.update(market_data)
        om.proceed_orders()  # update 1: order fill 1/10 from 1 (0.1)

        self.assertEqual("maker", order.state)
        self.assertEqual("hold tickers BTC/USDT", order.order_command)

        # maker price (ask) below threshold

        market_data = {"tickers": {"BTC/USDT": {"ask": 0.6, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()  # update 2: order fill 2/10 from 1 (0.)

        self.assertEqual(order.state, "maker")
        self.assertEqual("cancel tickers BTC/USDT", order.order_command)
        self.assertIn("#below_threshold_maker", order.tags)
        self.assertEqual(0.2, order.filled)

        # first trade order canceled. new trade order request for maker price 0.999
        market_data = {"tickers": {"BTC/USDT": {"ask": 0.999, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertEqual(0.999, order.price)
        self.assertEqual(0.2, order.orders_history[-1].filled)
        self.assertEqual(order.state, "maker")
        self.assertEqual("new tickers BTC/USDT", order.order_command)
        self.assertEqual(0.2, order.filled)

        # new order created
        market_data = {"tickers": {"BTC/USDT": {"ask": 0.999, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertEqual(0.2, order.filled)
        self.assertEqual("open", order.active_trade_order.status)
        self.assertEqual(0.8, order.active_trade_order.amount)

        # 1st update of the new trade order. filled 1/10 of the new order (0.08 from 0.8)
        market_data = {"tickers": {"BTC/USDT": {"ask": 0.999, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertEqual(0.28, order.filled)

    def test_multi_maker_fill_from_ticker(self):

        ex = ccxtExchangeWrapper.load_from_id("binancae") # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers_maker.csv")

        om = ActionOrderManager(ex)
        om.offline_order_updates = 10  # number of updates to fill order from offline data

        order = MakerStopLossOrder.create_from_start_amount(
            symbol="BTC/USDT",
            start_currency="BTC",
            start_amount=1,
            dest_currency="USDT",
            target_amount=1,
            cancel_threshold=0.001,
            maker_price_threshold=-0.01,
            maker_order_max_updates=4,
            taker_price_threshold=-0.02,
            taker_order_max_updates=5,
            threshold_check_after_updates=6
        )

        om.add_order(order)

        while om.have_open_orders():
            market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.99}}}
            om.data_for_orders.update(market_data)
            om.proceed_orders()  # update 1: order creation

        self.assertEqual("closed", order.status)
        self.assertEqual(1, order.filled_start_amount)
        self.assertEqual("maker", order.state)
        self.assertNotIn("#below_threshold_maker", order.tags)

        # number of trade orders created:
        # each order fills 4/10 of whole amount
        # ... should be 20 ;)
        self.assertEqual(20, len(order.orders_history))

    def test_maker_force_taker_updates(self):
        ex = ccxtExchangeWrapper.load_from_id("binancae") # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers_maker.csv")

        om = ActionOrderManager(ex)
        om.offline_order_updates = 10  # number of updates to fill order from offline data

        order = MakerStopLossOrder.create_from_start_amount(
            symbol="BTC/USDT",
            start_currency="BTC",
            start_amount=1,
            dest_currency="USDT",
            target_amount=1,
            cancel_threshold=0.001,
            maker_price_threshold=-0.01,
            maker_order_max_updates=4,
            force_taker_updates=2,
            taker_price_threshold=-0.02,
            taker_order_max_updates=5,
            threshold_check_after_updates=6
        )

        om.add_order(order)

        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertIn("#force_taker_max_maker_updates", order.tags)
        self.assertEqual("taker", order.state)
        self.assertEqual("cancel tickers BTC/USDT", order.order_command)

        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertEqual("new tickers BTC/USDT", order.order_command)
        self.assertEqual(0.99, order.active_trade_order.price)
        self.assertEqual("taker", order.state)

        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertEqual(0.99, order.active_trade_order.price)
        self.assertEqual("taker", order.state)
        self.assertEqual(1, len(order.orders_history))

    def test_maker_threshold_triggered(self):
        ex = ccxtExchangeWrapper.load_from_id("binancae")  # type: ccxtExchangeWrapper
        ex.set_offline_mode("test_data/markets.json", "test_data/tickers_maker.csv")

        om = ActionOrderManager(ex)
        om.offline_order_updates = 10  # number of updates to fill order from offline data

        order = MakerStopLossOrder.create_from_start_amount(
            symbol="BTC/USDT",
            start_currency="BTC",
            start_amount=1,
            dest_currency="USDT",
            target_amount=1,
            cancel_threshold=0.001,
            maker_price_threshold=-0.01,
            maker_order_max_updates=4,
            force_taker_updates=50,
            taker_price_threshold=-0.02,
            taker_order_max_updates=5,
            threshold_check_after_updates=6
        )

        om.add_order(order)

        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.99}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertEqual("maker", order.state)

        # let's trigger taker threshold - bid price
        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.97}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertEqual(0.2, order.filled)
        self.assertEqual("taker", order.state)
        self.assertEqual("cancel tickers BTC/USDT", order.order_command)
        self.assertIn("#below_threshold_taker_price", order.tags)

        # let's trigger taker threshold - bid price
        market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.97}}}
        om.data_for_orders.update(market_data)
        om.proceed_orders()

        self.assertEqual("taker", order.state)
        self.assertEqual("new tickers BTC/USDT", order.order_command)
        self.assertEqual(1, len(order.orders_history))
        self.assertEqual(0.97, order.active_trade_order.price)

        first_order_id = order.get_active_order().internal_id
        price = 0.96
        while om.have_open_orders():
            market_data = {"tickers": {"BTC/USDT": {"ask": 1, "bid": 0.96}}}
            om.data_for_orders.update(market_data)
            om.proceed_orders()

            if om.get_closed_orders():
                price = price * 0.99

            if order.active_trade_order is not None and order.active_trade_order.internal_id not in ("", first_order_id):
                self.assertEqual(price, order.active_trade_order.price)

            self.assertEqual("taker", order.state)


        self.assertEqual(1, order.filled)
        self.assertEqual(15, len(order.orders_history))
        self.assertEqual(1, sum(o.filled for o in order.orders_history))



    def test_force_taker(self):
        """
        if total updates in maker state exceed force_taker_updates
        """
        pass


if __name__ == '__main__':
    unittest.main()
