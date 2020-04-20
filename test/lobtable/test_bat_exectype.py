import unittest
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable


class BidAskTableOrdersTestLimitOrder(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BidAskTableOrdersTestLimitOrder, self).__init__(*args, **kwargs)
        self.colnames = ['contract', 'creation_time', 'order_id', 'direction', 'exec_type', 'price', 'size', 'expiration_time']
        # Exectype = Limit / Stop / StopLimit / Market
        self.data = {
            'limit':
                [['AAPL', 0.117459617, 10, 1,  0, 15, 1, 100],   # Buy  Limit $15
                 ['AAPL', 0.233423432, 11, -1, 0, 10, 1, 100]],  # => Order executes at 15
            'limit_multiple':
                [['AAPL', 0.117459617, 10, 1,  0, 20, 1, 100],  # Buy  Limit 20 => (Accepted)
                 ['AAPL', 0.217459617, 11, -1, 0, 30, 1, 100],  # Sell Limit 30 => (Accepted)
                 ['AAPL', 0.317459617, 12, 1,  0, 40, 1, 100],  # Buy  Limit 40 => (Completed, Completed)
                 ['AAPL', 0.433423432, 13, -1, 0, 50, 1, 100]],  # Sell Limit 50 => (Accepted)
            'limit_multiple_partial':
                [['AAPL', 0.117459617, 10, 1,  0, 20, 1, 100],  # Buy  Limit 20 => (Accepted)
                 ['AAPL', 0.217459617, 11, -1, 0, 30, 1, 100],  # Sell Limit 30 => (Accepted)
                 ['AAPL', 0.317459617, 12, 1,  0, 40, 5, 100],  # Buy  Limit 40 => (Completed, Partial)
                 ['AAPL', 0.433423432, 13, -1, 0, 50, 1, 100]]  # Sell Limit 50 => (Accepted)
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
    def test_price_execution_two_limit_orders(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        ba_table.handle_order(self.orders['limit'][0], self.orders['limit'][0].creation_time)
        sell_notification = ba_table.handle_order(self.orders['limit'][1], self.orders['limit'][1].creation_time)
        self.assertEqual(len(sell_notification.completed), 2)
        for order in sell_notification.completed:
            self.assertEqual(len(order.trades), 1)
            self.assertEqual(order.trades[0][0], 0.233423432)
            self.assertEqual(order.trades[0][1], 15)

    # @unittest.skip("skip")
    def test_price_execution_multiple(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['limit_multiple']):
            notification = ba_table.handle_order(order, order.creation_time)
            if i == 0:
                self.assertEqual(len(notification.accepted), 1)
            elif i == 1:
                self.assertEqual(len(notification.accepted), 1)
            elif i == 2:
                self.assertEqual(len(notification.completed), 2)
            elif i == 3:
                self.assertEqual(len(notification.accepted), 1)
                self.assertEqual(len(notification.partial_completed), 0)
                self.assertEqual(len(notification.completed), 0)

    # @unittest.skip("skip")
    def test_price_execution_multiple_partial(self):
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        for i, order in enumerate(self.orders['limit_multiple_partial']):
            notification = ba_table.handle_order(order, order.creation_time)
            if i == 0:
                self.assertEqual(len(notification.accepted), 1)
            elif i == 1:
                self.assertEqual(len(notification.accepted), 1)
            elif i == 2:
                self.assertEqual(len(notification.completed), 1)
                self.assertEqual(len(notification.partial_completed), 1)
            elif i == 3:
                self.assertEqual(len(notification.accepted), 1)
                self.assertEqual(len(notification.partial_completed), 0)
                self.assertEqual(len(notification.completed), 0)



if __name__ == '__main__':
    unittest.main()
