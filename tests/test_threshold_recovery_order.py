from .context import *
import tkgpro
from tkgpro import ThresholdRecoveryOrder
import unittest
import copy


class ThresholdThresholdRecoverOrderBasicTestSuite(unittest.TestCase):

    def test_comparison_eq(self):
        rm1 = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131)
        rm2 = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131)

        self.assertEqual(rm1, rm1)
        self.assertNotEqual(rm1, rm2)

        rm2.id = rm1.id
        self.assertEqual(rm1, rm1)

        rm2 = copy.copy(rm1)
        self.assertEqual(rm1, rm2)

        rm2.status = "closed"
        self.assertNotEqual(rm1, rm2)

        rm2 = copy.copy(rm1)
        rm2.filled = 1
        self.assertNotEqual(rm1, rm2)


class ThresholdThresholdRecoverOrderTestSuite(unittest.TestCase):
    

    def test_amount_for_best_dest_price(self):
        rm = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131)
        price = rm._get_recovery_price_for_best_dest_amount()

        self.assertAlmostEqual(price, 0.00032485, 8)
        self.assertAlmostEqual(rm.best_price, 0.00032485, 8)

    def test_create_trade_order(self):
        rm = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131)
        order = rm._create_recovery_order(rm._get_recovery_price_for_best_dest_amount())

        # check if we have a command for getting tickers data after order creation
        self.assertEqual(rm.order_command, "new tickers ADA/ETH")

        self.assertEqual(order.dest_currency, "ETH")
        self.assertEqual(order.amount, 1000)
        self.assertEqual(order.side, "sell")

        self.assertEqual(rm.amount, 1000)

    def test_update_from_exchange(self):
        ro = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131, taker_price_threshold=-0.01)

        # update 1 - partial fill
        resp = {"status": "open", "filled": 500, "cost": 0.32485131/2}

        # will update without market data
        ro.update_from_exchange(resp)

        self.assertEqual(ro.filled_start_amount, 500)
        self.assertEqual(ro.filled, 500)
        self.assertEqual(ro.status, "open")
        self.assertEqual(ro.state, "best_amount")
        self.assertEqual(ro.order_command, "hold tickers ADA/ETH")
        self.assertEqual(ro.filled_price, ro.active_trade_order.price)

        # update with marker_data
        market_data = [{"ask": 0.00032487, "bid": 0.00032483}]

        ro.update_from_exchange(resp, market_data)

        self.assertEqual( (0.00032483/0.00032485131) - 1, ro._prev_price_diff)
        self.assertEqual(ro.filled_start_amount, 500)
        self.assertEqual(ro.filled, 500)
        self.assertEqual(ro.status, "open")
        self.assertEqual(ro.state, "best_amount")
        self.assertEqual(ro.order_command, "hold tickers ADA/ETH")
        self.assertEqual(ro.filled_price, ro.active_trade_order.price)

    def test_fill_best_amount(self):

        ro = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131)

        # update 1 - partial fill
        resp = {"status": "open", "filled": 500, "cost": 0.32485131/2}
        ro.update_from_exchange(resp)
        self.assertEqual(ro.filled_start_amount, 500)
        self.assertEqual(ro.filled, 500)
        self.assertEqual(ro.status, "open")
        self.assertEqual(ro.state, "best_amount")
        self.assertEqual(ro.order_command, "hold tickers ADA/ETH")
        self.assertEqual(ro.filled_price, ro.active_trade_order.price)

        # update 2 - complete fill
        resp = {"status": "closed", "filled": 1000, "cost": 0.32485131}
        ro.update_from_exchange(resp)
        self.assertEqual(ro.filled_start_amount, 1000)
        self.assertEqual(ro.filled, 1000)
        self.assertEqual(ro.status, "closed")
        self.assertEqual(ro.order_command, "")
        self.assertEqual(ro.state, "best_amount")

        self.assertEqual(1, len(ro.orders_history))

    def test_cancel_best_amount_because_of_threshold(self):

        # sell order
        ro = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131, -0.02)

        # update 1 - partial fill
        resp = {"status":"open", "filled": 500, "cost": 0.32485131/2}
        ro.update_from_exchange(resp)
        self.assertEqual(ro.filled_start_amount, 500)
        self.assertEqual(ro.filled, 500)
        self.assertEqual(ro.status, "open")
        self.assertEqual(ro.state, "best_amount")
        self.assertEqual(ro.order_command, "hold tickers ADA/ETH")

        market_data = [{"bid": 0.00032485131*(1-0.021)}]
        ro.update_from_exchange(resp, market_data)

        self.assertEqual("cancel tickers ADA/ETH", ro.order_command)
        self.assertIn("#below_threshold", ro.tags)

        # buy order
        ro = ThresholdRecoveryOrder("ADA/ETH", "ETH", 0.32485131, "ADA", 1000, -0.02)

        # update 1 - partial fill
        resp = {"status": "open", "filled": 500, "cost": 0.32485131 / 2}
        ro.update_from_exchange(resp)
        self.assertEqual(ro.filled_start_amount, 0.32485131 / 2)
        self.assertEqual(ro.filled, 500)
        self.assertEqual(ro.status, "open")
        self.assertEqual(ro.state, "best_amount")
        self.assertEqual(ro.order_command, "hold tickers ADA/ETH")

        market_data = [{"ask": 0.00032485131 * (1 + 0.021)}]
        ro.update_from_exchange(resp, market_data)

        self.assertEqual("cancel tickers ADA/ETH", ro.order_command)
        self.assertIn("#below_threshold", ro.tags)

    def test_fill_market_price_from_1st_order(self):

        ro = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131, taker_price_threshold=-0.01)

        # updates max_updates -1 : order should be partially filled
        # price above threshold
        for i in range(1, ro.max_best_amount_orders_updates):
            resp = {"status": "open", "filled": 500, "cost": 0.32485131/2}
            ro.update_from_exchange(resp, [ {"ask": 1, "bid": ro.best_price*(1-0.009)}])

            self.assertEqual(ro.filled_start_amount, 500)
            self.assertEqual(ro.filled, 500)
            self.assertEqual(ro.status, "open")
            self.assertEqual(ro.state, "best_amount")
            self.assertEqual(ro.order_command, "hold tickers ADA/ETH")
            self.assertAlmostEqual(ro._prev_price_diff, -0.009, 8)

        # last order update before the cancelling active trade order
        resp = {"status": "open", "filled": 500, "cost": 0.32485131 / 2}
        ro.update_from_exchange(resp)
        self.assertEqual(ro.order_command, "cancel tickers ADA/ETH")

        # active trade order is cancelled - the command for the new order
        ro.update_from_exchange({"status": "canceled"}, [{"ask": 1, "bid": 0.00032483}])
        self.assertEqual(ro.order_command, "new")

        # parameters of new order: market price and amount of start curr which left to fill
        self.assertEqual(ro.active_trade_order.price, 0.00032483)
        self.assertEqual(ro.active_trade_order.amount, 500)

        self.assertEqual(ro.filled_start_amount, 500)
        self.assertEqual(ro.filled_dest_amount, 0.32485131/2)
        self.assertEqual(ro.filled, 500)
        self.assertEqual(len(ro.orders_history), 1)
        self.assertEqual(ro.orders_history[0].status, "canceled")

        # new order created and started to fill
        ro.update_from_exchange({"status": "open", "filled": 100})
        self.assertEqual(ro.filled, 600)
        self.assertEqual(ro.state, "market_price")
        self.assertEqual(ro.status, "open")
        self.assertEqual(ro.active_trade_order.status, "open")
        self.assertEqual(ro.active_trade_order.filled, 100)

        ro.update_from_exchange({"status": "open", "filled": 200})
        self.assertEqual(ro.active_trade_order.filled, 200)
        self.assertEqual(ro.filled, 700)

        ro.update_from_exchange({"status": "closed", "filled": 500})
        self.assertEqual(ro.active_trade_order, None)
        self.assertEqual(ro.orders_history[1].filled, 500)

        self.assertEqual(ro.filled, 1000)
        self.assertEqual(ro.status, "closed")
        self.assertEqual(ro.state, "market_price")
        self.assertEqual(ro.order_command, "")
        self.assertEqual(2, len(ro.orders_history))


    def test_fill_market_price_6_orders(self):

        ro = ThresholdRecoveryOrder("ADA/ETH", "ADA", 1000, "ETH", 0.32485131)

        # best_amount filled with zero result
        for i in range(1, ro.max_best_amount_orders_updates+1):
            resp = {"status": "open", "filled": 0, "cost": 0}
            ro.update_from_exchange(resp)
        self.assertEqual(ro.filled, 0)
        self.assertEqual(ro.status, "open")
        self.assertEqual(ro.state, "best_amount")
        self.assertEqual(ro.order_command, "cancel tickers ADA/ETH")

        ro.update_from_exchange({"status": "canceled", "filled": 500}, [{"ask": 2, "bid": 0.00032483}])
        self.assertEqual(ro.order_command, "new")
        self.assertEqual(ro.active_trade_order.price, 0.00032483)  # if taker price

        for i in range(1, 5):  # i  will be from 1 to 4 - 4 orders in total
            ro.update_from_exchange({"status": "open", "filled": 0}, [{"ask": 1, "bid": 0.00032483}])

            self.assertEqual(ro.state, "market_price")
            self.assertEqual(ro.order_command, "hold tickers ADA/ETH")
            self.assertEqual(len(ro.orders_history), i)
            self.assertEqual(ro.filled, sum(item.filled for item in ro.orders_history))

            for j in range(1, ro.max_order_updates):
                ro.update_from_exchange({"status": "open", "filled": 10}, [{"ask": 1, "bid": 0.00032483}])

            ro.update_from_exchange({"status": "open", "filled": 100}, [{"ask": 1, "bid": 0.00032483}])
            self.assertEqual(ro.order_command, "cancel tickers ADA/ETH")

            ro.update_from_exchange({"status": "canceled", "filled": 100}, [{"ask": 1, "bid": 0.00032483}])

        self.assertEqual(ro.order_command, "new")  # 6th order
        ro.update_from_exchange({"status": "closed", "filled": 100}, [{"ask": 1, "bid": 0.00032483}])
        self.assertEqual(ro.filled, 1000)

        self.assertEqual(6, len(ro.orders_history))

    def test_1st_order_executed_better(self):
        pass

    def test_2nd_order_executed_better(self):
        pass

if __name__ == '__main__':
    unittest.main()

