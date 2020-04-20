import unittest
import heapq
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable


class BidAskTableTestCancelations(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BidAskTableTestCancelations, self).__init__(*args, **kwargs)
        self.colnames = ['contract', 'creation_time', 'order_id', 'direction', 'exec_type', 'price', 'size', 'expiration_time']
        self.data_with_errors = {
            'single_canceled_rejected':
                [['TSLA', 0.017459617, 10, 1, 0, 10, 1, 100],
                 ['TSLA', None,        11, 0, 0, 10, 1, 100]],  # => is updated in test
        }
        self.data = {
            'single_canceled_accepted':
                [['TSLA', 12, 10, 1, 0, 10, 1, 100],
                 ['TSLA', 90, 10, 0, 0, 10, 1, 100]],
            'single_canceled_accepted_with_noise':
                [['TSLA', 0.017459617, 10, 1, 0, 10, 1, 100],
                 ['TSLA', 0.117459617, 21, 1, 0, 50, 1, 100],   # noise
                 ['TSLA', 0.217459617, 22, 1, 0, 10, 1, 100],   # noise
                 ['TSLA', 0.317459617, 23, 1, 0, 1,  1, 100],   # noise
                 ['TSLA', 0.433423432, 10, 0, 0, 10, 1, 100]],
            'market_cancellation_accepted':
                [['TSLA', 1, 10, 1, 3, None, 1, 100],
                 ['TSLA', 2, 10, 0, 0, 10,   1, 100]],
            'expired_vs_cancelled':
                [['TSLA', 1,    10, 1, 3, None, 1, 100],   # => market order
                 ['TSLA', 5,    10, 0, 0, 10,   1, 100],   # => cancelation ok => (Canceled, Complete)
                 ['TSLA', 10,   11, 1, 3, None, 1, 14],    # => market order (11)
                 ['TSLA', 15,   11, 0, 0, 10,   1, 100]],   # => market order (11) expired at t=14 => (Expired, Rejected)
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

    # TESTS

    # @unittest.skip("skip")
    def test_expired_vs_cancelled(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['expired_vs_cancelled']):
            notification = ba_table.handle_order(order, order.creation_time)
            if i == 1:
                self.assertEqual(len(notification.canceled), 1)
                self.assertEqual(len(notification.completed), 1)
            if i == 3:
                self.assertEquals(len(notification.expired), 1)
                self.assertEqual(len(notification.rejected), 1)

    # @unittest.skip("skip")
    def test_handle_order_expired_raises_exception(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        ls = self.data_with_errors['single_canceled_rejected'][0]
        d = {self.colnames[j]: ls[j] for j, _ in enumerate(ls)}
        d['creator_id'] = 'false_agent'
        order1 = OrderCreator.create_order_from_dict(d)
        ba_table.handle_order(order1, order1.creation_time)
        # Second
        ls2 = self.data_with_errors['single_canceled_rejected'][1]
        d2 = {self.colnames[j]: ls2[j] for j, _ in enumerate(ls2)}
        d2['creation_time'] = ba_table.current_time - 1
        d2['creator_id'] = 'false_agent'
        order2 = OrderCreator.create_order_from_dict(d2)

        self.assertRaises(Exception, ba_table.handle_order, order2, order2.creation_time)

    # @unittest.skip("skip")
    def test_market_order_cancelled(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['market_cancellation_accepted']):
            notification = ba_table.handle_order(order, order.creation_time)
        # First order is canceled
        self.assertEquals(len(notification.canceled), 1)
        self.assertEquals(len(notification.completed), 1)


    # @unittest.skip("skip")
    def test_accepted_and_canceled(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['single_canceled_accepted']):
            notification = ba_table.handle_order(order, order.creation_time)
        # First order is canceled
        self.assertEquals(len(notification.canceled), 1)
        self.assertEquals(len(notification.completed), 1)
        self.assertEquals(ba_table.queue_observer.bid_size(), 0)
        self.assertEquals(ba_table.queue_observer.ask_size(), 0)

    # @unittest.skip("skip")
    def test_accepted_and_canceled_with_noise(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['single_canceled_accepted_with_noise']):
            notification = ba_table.handle_order(order, order.creation_time)
        # First order is canceled
        self.assertEquals(len(notification.canceled), 1)
        self.assertEquals(len(notification.completed), 1)
        self.assertEquals(ba_table.queue_observer.bid_size(), 3)
        # Check that the queue keeps in order
        self.assertEquals(ba_table.queue_observer.best_bid().price, 50)
        self.assertEquals([order.price for order in heapq.nsmallest(3, ba_table.bid)], [50, 10, 1])

if __name__ == '__main__':
    unittest.main()
