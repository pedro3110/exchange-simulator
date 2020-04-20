from src.exchange.orders.order_creator import OrderCreator
from src.exchange.orders.order_utils import Direction, Exectype, OrderStatus
from src.exchange.orders.order import Order


class InitialOrder(Order):
    def __init__(self, contract, order_id, direction, price, size):
        initial_time = 0.0
        super(InitialOrder, self).__init__('Simulation',
                                           contract, initial_time, order_id, price, size, direction,
                                           Exectype.Limit, float('inf'), OrderStatus.Created)
        self.accept(initial_time)

    def set_order_id(self, order_id):
        self.m_orderId = order_id
        return 0


class InitialOrderCreator(OrderCreator):

    @classmethod
    def create_order(cls, contract, order_id, order_params):
        if order_params[0] == 'bid':
            order = InitialOrder(contract, order_id, Direction.Buy, order_params[1], order_params[2])
        elif order_params[0] == 'ask':
            order = InitialOrder(contract, order_id, Direction.Sell, order_params[1], order_params[2])
        else:
            raise Exception()
        return order
