# -*- coding: utf-8 -*-
from .context import tkgpro
from tkgpro import MakerStopLossOrder
from tkgcore import core
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

    def test_single_maker_fill_is_good(self):
        pass

    def test_multi_maker_fill_is_good(self):
        pass

    def test_maker_threshold_triggered(self):
        pass

    def test_single_taker_is_good(self):
        pass

    def test_multi_taker_fill_is_good(self):
        pass


if __name__ == '__main__':
    unittest.main()
