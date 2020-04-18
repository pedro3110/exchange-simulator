import unittest
from src.exchange.orders.order_utils import Exectype
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable


class BATMarketOrderTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BATMarketOrderTest, self).__init__(*args, **kwargs)
        self.colnames = ['contract', 'creation_time', 'order_id', 'direction', 'exec_type', 'price', 'size', 'expiration_time']
        self.data_with_error = {
            'single_market':
                [['AAPL', 0.017459617, 10, 1, 3, 10, 1, 100]],
        }
        self.data_ok = {
            'single_market':
                [['AAPL', 0.017459617, 10, 1, 3, None, 1, 100]],
            'three_market':
                [['AAPL', 0.017459617, 10, 1,  3, None, 1, 100],
                 ['AAPL', 0.027459617, 11, 1,  3, None, 1, 100],
                 ['AAPL', 0.038934456, 12, -1, 3, None, 1, 100]],
            'market_vs_limit':
                [['AAPL', 0.017459617, 10, 1,  3, None, 1, 100],
                 ['AAPL', 0.018934456, 11, -1, 0, 10,   1, 100]],
            'market_vs_limit_multiple':
                [['AAPL', 0.17459617, 10, 1,  0, 10,   1, 100],
                 ['AAPL', 0.27459617, 11, -1, 0, 20,   1, 100],
                 ['AAPL', 0.37459617, 12, 1,  3, None, 1, 100],   # => executes (11,12) at 20 (Complete, Complete)
                 ['AAPL', 0.48934456, 13, -1, 0, 10,   1, 100]],  # => executes (10,13) at 10 (Complete, Complete)
            'market_vs_limit_multiple_partial':
                [['AAPL', 0.17459617, 10, -1, 0, 10,   1, 100],
                 ['AAPL', 0.27459617, 11, -1, 0, 20,   1, 100],
                 ['AAPL', 0.37459617, 12, 1,  3, None, 5, 100],   # => executes (10,12){10}{C,P}+(11,12){20}{C,P}
                 ['AAPL', 0.48934456, 13, -1, 0, 10,   3, 100]],  # => executes (10,13){10}{C,C}
        }
        self.orders = dict()
        for k, v in self.data_ok.items():
            orders = []
            for i, ls in enumerate(v):
                d = {
                    self.colnames[j]: ls[j] for j, _ in enumerate(ls)
                }
                d['creator_id'] = 'false_agent'
                orders.append(OrderCreator.create_order_from_dict(d))
            self.orders[k] = orders

    # TESTS

    # @unittest.skip("skip")
    def test_market_order_with_none(self):
        ls = self.data_ok['single_market'][0]
        d = {self.colnames[j]: ls[j] for j, _ in enumerate(ls)}
        d['creator_id'] = 'false_agent'
        order = OrderCreator.create_order_from_dict(d)
        self.assertEquals(order.get_exec_type(), Exectype.Market)

    # @unittest.skip("skip")
    def test_market_order_with_integer_raises_exception(self):
        ls = self.data_with_error['single_market'][0]
        d = {self.colnames[j]: ls[j] for j, _ in enumerate(ls)}
        d['creator_id'] = 'false_agent'
        self.assertRaises(Exception, OrderCreator.create_order_from_dict, d)

    # @unittest.skip("skip")
    def test_three_market_orders(self):
        ba_table = LOBTable(contract='IBM')
        order1 = self.orders['three_market'][0]
        notification1 = ba_table.handle_order(order1, order1.creation_time)
        self.assertEquals(len(notification1.accepted), 1)
        order2 = self.orders['three_market'][1]
        notification2 = ba_table.handle_order(order2, order2.creation_time)
        self.assertEquals(len(notification2.accepted), 1)
        order3 = self.orders['three_market'][2]
        ba_table.handle_order(order3, order3.creation_time)
        # Final state of bid ask tables
        self.assertEqual(ba_table.queue_observer.market_bid_size(), 2)
        self.assertEqual(ba_table.queue_observer.market_ask_size(), 1)

    # @unittest.skip("skip")
    def test_market_vs_limit_order(self):
        ba_table = LOBTable(contract='IBM')
        order1 = self.orders['market_vs_limit'][0]
        notification1 = ba_table.handle_order(order1, order1.creation_time)
        self.assertEquals(len(notification1.accepted), 1)
        self.assertEquals(ba_table.queue_observer.market_bid_size(), 1)
        order2 = self.orders['market_vs_limit'][1]
        notification2 = ba_table.handle_order(order2, order2.creation_time)
        self.assertEquals(len(notification2.completed), 2)

    # @unittest.skip("skip")
    def test_limit_vs_market_multiple_order(self):
        ba_table = LOBTable(contract='IBM')
        for i, order in enumerate(self.orders['market_vs_limit_multiple']):
            notification = ba_table.handle_order(order, order.creation_time)
            if i == 2:
                self.assertEquals(len(notification.completed), 2)
            if i == 3:
                self.assertEquals(len(notification.completed), 2)

    # @unittest.skip("skip")
    def test_limit_vs_market_multiple_order_partial(self):
        ba_table = LOBTable(contract='IBM')
        for i, order in enumerate(self.orders['market_vs_limit_multiple_partial']):
            notification = ba_table.handle_order(order, order.creation_time)
            if i == 2:
                self.assertEquals(len(notification.completed), 2)
                self.assertEquals(len(notification.partial_completed), 1)
            if i == 3:
                self.assertEquals(len(notification.completed), 2)


if __name__ == '__main__':
    unittest.main()
