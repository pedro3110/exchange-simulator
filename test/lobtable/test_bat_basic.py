import unittest
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable


class BidAskTableTest3Orders(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BidAskTableTest3Orders, self).__init__(*args, **kwargs)
        self.colnames = ['contract', 'creation_time', 'order_id', 'direction', 'exec_type', 'price', 'size', 'expiration_time']
        self.data = {
            'expired':
                [['TSLA', 0.017459617, 10, 1,  0, 10, 1, 100],    # Buy order is accepted
                 ['TSLA', 101.3423432, 11, -1, 0, 10, 1, 200]],   # Sell order is accepted; expiration of order 10 is notified
            '2_buy_1_sell_completed':
                [['TSLA', 0.017459617, 10, 1,  0, 10, 1, 100],    # Buy order is accepted
                 ['TSLA', 0.3423432,   11, -1, 0, 11, 1, 100],    # Sell order is accepted but not completed (price too high)
                 ['TSLA', 0.5765765,   12, -1, 0, 10, 1, 100]],   # Buy & Sell orders are Completed (size bid == size best ask & price bid == price best ask)
            '2_buy_1_sell_partial':
                [['TSLA', 0.017459617, 10, 1, 0, 10, 1, 100],   # Buy order is accepted
                 ['TSLA', 0.3423432, 11, -1,  0, 11, 2, 100],   # Sell order is accepted but not completed (price too high)
                 ['TSLA', 0.5765765, 12, -1,  0, 10, 2, 100]],  # Buy=>Completed, Sell=>Partial (price < best ask)
            'multi_buy_multi_sell':
                [['TSLA', 0.017459617, 10,  1, 0, 20, 1, 100],   # First order matches with fourth (in price and are completed)
                 ['TSLA', 0.142343233, 11, -1, 0, 21, 2, 100],   # Second order matches with fifth (in price, are completed)
                 ['TSLA', 0.234563433, 13, -1, 0, 25, 5, 100],   # Noise. Sell order at a very high price
                 ['TSLA', 0.334563433, 14, -1, 0, 20, 1, 100],
                 ['TSLA', 0.476576533, 15,  1, 0, 21, 2, 100]],
            'repeated_id':
                [['TSLA', 0.017459617, 10, 1,  0, 10, 1, 100],   # Accepted
                 ['TSLA', 0.576576533, 10, -1, 0, 10, 2, 100]]   # Rejected: each order must have a different identifier
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
    def test_one_order_expired_after_time_passed(self):
        first_time = 90
        second_time = 110
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        order1 = self.orders['expired'][0]
        notification1 = ba_table.handle_order(order1, first_time)
        self.assertEquals(len(notification1.accepted), 1)
        order2 = self.orders['expired'][1]
        # When order2 arrives, order1 has expired!
        notification2 = ba_table.handle_order(order2, second_time)
        self.assertEquals(len(notification2.accepted), 1)
        self.assertEquals(len(notification2.expired), 1)

    # @unittest.skip("skip")
    def test_second_sell_completed(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['2_buy_1_sell_completed']):
            if i == 0:
                # First Buy Order
                notification = ba_table.handle_order(order, 0.12345)
                self.assertEquals(len(notification.accepted), 1)
            elif i == 1:
                # Sell Order
                notification = ba_table.handle_order(order, 0.23456)
                self.assertEquals(len(notification.accepted), 1)
            else:
                # Second Buy Order
                notification = ba_table.handle_order(order, 0.34567)
                self.assertEquals(len(notification.accepted), 0)
                self.assertEquals(len(notification.completed), 2)
                self.assertEquals(ba_table.queue_observer.bid_size(), 0)   # the second sell order matched completely 1st buy order
                self.assertEquals(ba_table.queue_observer.ask_size(), 1)   # the first sell order (price too high)

    # @unittest.skip("skip")
    def test_second_sell_partial(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['2_buy_1_sell_partial']):
            if i == 0:
                notification = ba_table.handle_order(order, 0.12345)
            elif i == 1:
                notification = ba_table.handle_order(order, 0.23456)
            else:
                notification = ba_table.handle_order(order, 0.34567)
                self.assertEquals(len(notification.accepted), 0)
                self.assertEquals(len(notification.partial_completed), 1)
                self.assertEquals(len(notification.completed), 1)
                self.assertEquals(ba_table.queue_observer.bid_size(), 0)  # the buy order executed completely
                self.assertEquals(ba_table.queue_observer.ask_size(), 2)  # remaining partial order + accepted order (price high)
                # remaining best ask: 1 contract at price 10
                self.assertEquals(ba_table.queue_observer.best_ask().m_orderId, 12)
                self.assertEquals(ba_table.queue_observer.best_ask().size_remaining, 1)

    # @unittest.skip("skip")
    def test_multi_buy_multi_sell(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['multi_buy_multi_sell']):
            notification = ba_table.handle_order(order, i) # orders are sent in order
        # After all orders are processed...
        self.assertEquals(ba_table.queue_observer.bid_size(), 0)  # 1-4 and 2-5 match exactly
        self.assertEquals(ba_table.queue_observer.ask_size(), 1)  # the order 3 did not match
        # Last notification contains information about de orders 2-5
        self.assertEquals(len(notification.completed), 2)
        notification_order_ids = notification.get_order_ids()
        self.assertEquals(len(notification_order_ids), 2)
        self.assertTrue(11 in notification_order_ids)
        self.assertTrue(15 in notification_order_ids)

    # @unittest.skip("skip")
    def test_reject_duplicated_id(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['repeated_id']):
            notification = ba_table.handle_order(order, i)  # orders are sent in order
        # Second order should be rejected
        self.assertEquals(len(notification.rejected), 1)
        self.assertEquals(len(notification.get_order_ids()), 1)

if __name__ == '__main__':
    unittest.main()
