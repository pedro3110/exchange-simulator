import unittest
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable


class BATStopOrderTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BATStopOrderTest, self).__init__(*args, **kwargs)
        self.colnames = ['contract', 'creation_time', 'order_id', 'direction', 'exec_type', 'price', 'size', 'expiration_time']
        self.data_with_error = {

        }
        self.data_ok = {
            'single_stop_market':
                [['AAPL', 1.23456, 10, 1, 1, 10, 1, 100]],  # Stop order. should have price = None
            'stop_mutates_to_market':
                [['AAPL', 1.23456, 11, 1,  1, 10, 1, 100],  # Stop
                 ['AAPL', 2.23456, 12, 1,  0, 9, 1, 100],   # Limit
                 ['AAPL', 3.23456, 13, -1, 0, 9, 1, 100]],  # Limit => (11,12){10}{C,C} => (10){Stop=>Market}
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
    def test_stop_accepted(self):
        ba_table = LOBTable(contract='IBM')
        order1 = self.orders['single_stop_market'][0]
        notification = ba_table.handle_order(order1, order1.creation_time)
        self.assertEquals(len(notification.accepted), 1)

    # @unittest.skip("skip")
    def test_stop_to_market(self):
        ba_table = LOBTable(contract='IBM')
        for i, order in enumerate(self.orders['stop_mutates_to_market']):
            notification = ba_table.handle_order(order, order.creation_time)
            if i == 2:
                self.assertEqual(len(notification.completed), 2)
                self.assertEqual(len(ba_table.stop), 0)
                self.assertEqual(len(ba_table.market_bid), 1)



if __name__ == '__main__':
    unittest.main()
