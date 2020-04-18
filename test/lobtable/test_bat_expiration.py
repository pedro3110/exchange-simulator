import unittest
from src.exchange.orders.order_utils import OrderStatus, Direction
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable


class BidAskTableTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BidAskTableTest, self).__init__(*args, **kwargs)
        self.colnames = ['contract', 'creation_time', 'order_id', 'direction', 'exec_type', 'price', 'size', 'expiration_time']
        self.data = {
            'basic':
                [['AAPL', None, 10, 1,  0, 10, 1, 100]],
            'basic_2':
                [['AAPL', 0.017459617, 10, 1, 0, 10, 1, 100],
                 ['AAPL', 90.2342343, 11, -1, 0, 10, 1, 100]],
            'with_expiration':
                [['AAPL', 0.017459617, 10, 1,  0, 10, 1, 110],
                 ['AAPL', 0.018934456, 11, -1, 0, 10, 1, 90]],
            'partial_buy':   # selling 1 order and buying 2 (Partial Buy, Completed Sell)
                [['AAPL', 0.017459617, 10, 1,  0, 10, 1, 100],
                 ['AAPL', 0.018934456, 11, -1, 0, 10, 2, 100]],
            'partial_sell':   # selling 2 orders and buying 1 (Partial Sell, Completed Buy)
                [['AAPL', 0.017459617, 10, -1, 0, 10, 2, 100],
                 ['AAPL', 0.018934456, 11, 1,  0, 10, 1, 100]],
            'expiration_before_match':
                [['AAPL', 0.1, 10, -1, 0, 10, 2, 1],      # order expires at t = 1.0
                 ['AAPL', 2.1, 11, 1,  0, 10, 2, 100]],   # order arrives at t = 2.1 => no match (+1 expiration)
            'multiple_expiration_before_match':
                [['AAPL', 0.1, 10, -1, 0, 10, 2, 1],  # order expires at t = 1.0
                 ['AAPL', 0.2, 11, -1, 0, 10, 2, 1],
                 ['AAPL', 0.3, 12, -1, 0, 10, 2, 1],
                 ['AAPL', 2.1, 13, 1,  0, 10, 2, 100]],  # order arrives at t = 2.1 => no match (+3 expirations)
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

    # @unittest.skip("skip")
    def test_multiple_expiration_before_match(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['multiple_expiration_before_match']):
            notification = ba_table.handle_order(order, order.creation_time)
            if i <= 2:
                self.assertEqual(len(notification.accepted), 1)
            elif i == 3:
                self.assertEqual(len(notification.expired), 3)
                self.assertEqual(len(notification.accepted), 1)

    # @unittest.skip("skip")
    def test_expiration_before_match(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        order1 = self.orders['expiration_before_match'][0]
        ba_table.handle_order(order1, order1.creation_time)
        order2 = self.orders['expiration_before_match'][1]
        notification_order2 = ba_table.handle_order(order2, order2.creation_time)
        self.assertEquals(len(notification_order2.accepted), 1)
        self.assertEquals(len(notification_order2.expired), 1)

    # @unittest.skip("skip")
    def test_expired_order(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        order = self.orders['basic'][0]
        notification = ba_table.handle_order(order, order.expiration_time + 1)
        self.assertEquals(len(notification.rejected), 1)
        self.assertEquals(notification.rejected[0].m_orderId, order.m_orderId)
        self.assertEquals(notification.rejected[0].get_status(), OrderStatus.Rejected)

    # @unittest.skip("skip")
    def test_rejected_new_order_expired(self):
        current_time = 100
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        buy_order_1 = self.orders['with_expiration'][0]
        notification_buy_1 = ba_table.handle_order(buy_order_1, buy_order_1.creation_time)
        self.assertEquals(len(notification_buy_1.accepted), 1)
        sell_order = self.orders['with_expiration'][1]
        notification_sell = ba_table.handle_order(sell_order, current_time)
        self.assertEquals(len(notification_sell.rejected), 1)
        self.assertEquals(ba_table.queue_observer.bid_size(), 1)
        self.assertEquals(ba_table.queue_observer.ask_size(), 0)

    # @unittest.skip("skip")
    def test_completed_order(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        buy_order_1 = self.orders['basic_2'][0]
        notification_buy_1 = ba_table.handle_order(buy_order_1, buy_order_1.creation_time)
        self.assertEquals(len(notification_buy_1.accepted), 1)
        sell_order = self.orders['basic_2'][1]
        notfication_sell = ba_table.handle_order(sell_order, sell_order.creation_time)
        self.assertEquals(len(notfication_sell.completed), 2)
        self.assertTrue(ba_table.queue_observer.bid_empty(), True)
        self.assertTrue(ba_table.queue_observer.ask_empty(), True)

    # @unittest.skip("skip")
    def test_partial_direct_buy(self):
        current_time = 90
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        buy_order_1 = self.orders['partial_buy'][0]
        notification_buy_1 = ba_table.handle_order(buy_order_1, buy_order_1.creation_time)
        self.assertEquals(len(notification_buy_1.accepted), 1)
        sell_order = self.orders['partial_buy'][1]
        notification_sell = ba_table.handle_order(sell_order, sell_order.creation_time)
        self.assertEquals(len(notification_sell.partial_completed), 1)
        self.assertEquals(len(notification_sell.completed), 1)

    # @unittest.skip("skip")
    def test_partial_direct_sell(self):
        current_time = 90
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        sell_order = self.orders['partial_sell'][0]
        notification_sell = ba_table.handle_order(sell_order, sell_order.creation_time)
        self.assertEquals(len(notification_sell.accepted), 1)
        buy_order = self.orders['partial_sell'][1]
        notification_buy = ba_table.handle_order(buy_order, buy_order.creation_time)
        self.assertEquals(len(notification_buy.partial_completed), 1)
        self.assertEquals(len(notification_buy.completed), 1)

        self.assertEquals(notification_buy.completed[0].direction, Direction.Buy)
        self.assertEquals(notification_buy.partial_completed[0].direction, Direction.Sell)

if __name__ == '__main__':
    unittest.main()
