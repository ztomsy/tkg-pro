# -*- coding: utf-8 -*-
from .context import tkgpro
from tkgpro import MakerStopLossOrder
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


if __name__ == '__main__':
    unittest.main()
