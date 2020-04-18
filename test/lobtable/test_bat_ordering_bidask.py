import unittest
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable
import heapq


class BidAskTableOrdersTestTableOrdering(unittest.TestCase):
    """
    Test ordering 1. Price, 2. Time, 3. Size
    """
    def __init__(self, *args, **kwargs):
        super(BidAskTableOrdersTestTableOrdering, self).__init__(*args, **kwargs)
        self.colnames = ['contract', 'creation_time', 'order_id', 'direction', 'exec_type', 'price', 'size', 'expiration_time']
        # Exectype = Limit / Stop / StopLimit / Market
        self.data = {
            'limit':
                [['AAPL', 0.117459617, 10, 1,  0, 15, 1, 100],   # Buy  Limit $15
                 ['AAPL', 0.233423432, 11, -1, 0, 10, 1, 100]],  # Sell Limit $10 => execute at $15 (prioritize creation_time)
            'bid_ordering_0':
                [['AAPL', 0.444444444, 13, 1, 0, 60, 1, 100],
                 ['AAPL', 0.555555555, 14, 1, 0, 70, 1, 100],
                 ['AAPL', 0.666666666, 15, 1, 0, 80, 1, 100],  # => bid ordering: [15, 14, 13]
                 ['AAPL', 0.777777777, 16, -1, 0, 180, 1, 100],
                 ['AAPL', 0.888888888, 17, -1, 0, 160, 1, 100],
                 ['AAPL', 0.999999999, 18, -1, 0, 170, 1, 100]],  # => ordering: [17, 18, 16]
            'bid_ordering_1':
                [['AAPL', 0.444444444, 13, 1, 0, 60, 1, 100],
                 ['AAPL', 0.555555555, 14, 1, 0, 60, 3, 100],
                 ['AAPL', 0.666666666, 15, 1, 0, 60, 2, 100],   # => bid ordering: [14, 15, 13]
                 ['AAPL', 0.777777777, 16, -1, 0, 80, 1, 100],
                 ['AAPL', 0.888888888, 17, -1, 0, 80, 3, 100],
                 ['AAPL', 0.999999999, 18, -1, 0, 80, 2, 100]],  # => ordering: [17, 18, 16]
            'bid_ordering_3':
                [['AAPL', 0.444444444, 10, 1, 0, 90, 1, 100],
                 ['AAPL', 0.555555555, 11, 1, 0, 80, 3, 100],
                 ['AAPL', 0.666666666, 12, 1, 0, 80, 5, 100],
                 ['AAPL', 0.777777777, 13, 1, 0, 80, 4, 100],
                 ['AAPL', 0.888888888, 14, 1, 0, 60, 10, 100],
                 ['AAPL', 0.999999999, 15, 1, 0, 60, 10, 100]],  # => bid ordering: [10, 12, 14, 11, 14, 15]
            'bid_ordering_4':
                [['AAPL', 0.444444444, 13, 1, 0, 60, 3, 100],
                 ['AAPL', 0.555555555, 14, 1, 0, 60, 1, 100],
                 ['AAPL', 0.666666666, 15, 1, 0, 60, 2, 100],
                 ['AAPL', 0.777777777, 16, -1, 0, 60, 3, 100],
                 ['AAPL', 0.888888888, 17, -1, 0, 60, 1, 100],
                 ['AAPL', 0.999999999, 18, -1, 0, 60, 2, 100]]
        }
        self.orders = dict()
        for k, v in self.data.items():
            orders = []
            for i, ls in enumerate(v):
                d = {
                    self.colnames[j]: ls[j] for j, _ in enumerate(ls)
                }
                d['creator_id'] = 'false_agent'
                orders.append(OrderCreator.create_order_from_dict(d))
            self.orders[k] = orders

    # Tests
    # @unittest.skip("skip")
    def test_bid_ordering_0(self):
        contract = 'AAPL'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['bid_ordering_0']):
            ba_table.handle_order(order, order.creation_time)
        # Asserts
        self.assertEquals([order.m_orderId for order in heapq.nsmallest(5, ba_table.bid)], [15, 14, 13])
        self.assertEquals([order.m_orderId for order in heapq.nsmallest(5, ba_table.ask)], [17, 18, 16])

    # @unittest.skip("skip")
    def test_bid_ordering_1(self):
        contract = 'AAPL'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['bid_ordering_1']):
            ba_table.handle_order(order, order.creation_time)
        # Asserts
        self.assertEquals([order.m_orderId for order in heapq.nsmallest(5, ba_table.bid)], [13, 14, 15])
        self.assertEquals([order.m_orderId for order in heapq.nsmallest(5, ba_table.ask)], [16, 17, 18])

    # @unittest.skip("skip")
    def test_bid_ordering_3(self):
        contract = 'AAPL'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['bid_ordering_3']):
            ba_table.handle_order(order, order.creation_time)
        self.assertEquals([order.m_orderId for order in heapq.nsmallest(6, ba_table.bid)], [10, 11, 12, 13, 14, 15])

    # @unittest.skip("skip")
    def test_bid_ordering_4(self):
        contract = 'AAPL'
        b = LOBTable(contract=contract)
        notification1 = b.handle_order(self.orders['bid_ordering_4'][0], self.orders['bid_ordering_4'][0].creation_time)
        notification2 = b.handle_order(self.orders['bid_ordering_4'][1], self.orders['bid_ordering_4'][1].creation_time)
        notification3 = b.handle_order(self.orders['bid_ordering_4'][2], self.orders['bid_ordering_4'][2].creation_time)
        notification4 = b.handle_order(self.orders['bid_ordering_4'][3], self.orders['bid_ordering_4'][3].creation_time)
        notification5 = b.handle_order(self.orders['bid_ordering_4'][4], self.orders['bid_ordering_4'][4].creation_time)
        notification6 = b.handle_order(self.orders['bid_ordering_4'][5], self.orders['bid_ordering_4'][5].creation_time)
        # Checks
        self.assertEquals(len(notification1.accepted), 1)
        self.assertEquals(len(notification2.accepted), 1)
        self.assertEquals(len(notification3.accepted), 1)

        self.assertEquals(len(notification4.partial_completed), 0)
        self.assertEquals(len(notification4.completed), 2)

        self.assertEquals(len(notification5.partial_completed), 0)
        self.assertEquals(len(notification5.completed), 2)

        self.assertEquals(len(notification6.completed), 2)


if __name__ == '__main__':
    unittest.main()
