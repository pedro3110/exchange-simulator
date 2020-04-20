import unittest
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable


class BATOrderCreationTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(BATOrderCreationTest, self).__init__(*args, **kwargs)
        self.colnames = ['contract', 'creation_time', 'order_id', 'direction', 'exec_type', 'price', 'size', 'expiration_time']
        self.data_with_error = {
            'expired_order':
                [['AAPL', 25, 12, 0, 0, 10, 1, 5]],   # creation_time = 25 > 5 = expiration
        }
        self.data_ok = {
            'ordered':
                [['AAPL', None, 12, 0, 0, 10, 1, 5]],
            'unordered':
                [['AAPL', 10, 10, 1, 0, 10, 1, 11],
                 ['AAPL', 5,  11, 1, 0, 10, 1, 6]],  # => unordered
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

    # @unittest.skip("skip")
    def test_initialize_expired_order_raise_exception(self):
        ls = self.data_with_error['expired_order'][0]
        d = {self.colnames[j]: ls[j] for j, _ in enumerate(ls)}
        d['creator_id'] = 'false_agent'
        self.assertRaises(Exception, OrderCreator.create_order_from_dict, d)

    # @unittest.skip("skip")
    def test_handle_expired_order_raise_exception(self):
        ls = self.data_ok['ordered'][0]
        d = {self.colnames[j]: ls[j] for j, _ in enumerate(ls)}
        d['creator_id'] = 'false_agent'
        order = OrderCreator.create_order_from_dict(d)
        order.creation_time = order.expiration_time + 1
        contract = 'IBM'
        ba_table = LOBTable(contract=contract)
        self.assertRaises(Exception, ba_table.handle_order, order)

    # @unittest.skip("skip")
    def test_bat_reject_unordered_expired_order(self):
        contract = 'IBM'
        b = LOBTable(contract=contract)
        notification1 = b.handle_order(self.orders['unordered'][0], self.orders['unordered'][0].creation_time)
        self.assertEquals(len(notification1.accepted), 1)
        self.assertRaises(Exception, b.handle_order, self.orders['unordered'][1], self.orders['unordered'][1].creation_time)

if __name__ == '__main__':
    unittest.main()
