from src.exchange.orders.order_utils import OrderStatus, Exectype, Direction
from src.utils.debug import Debug
import operator
import numbers


class Order(Debug):
    """
    Each market will have certain rules. The orders must be sent in a specific format, determined by it. By default
    the order is a Market order
    Attributes
    ----------
    m_orderId : Integer  (Non mutable)
    creation_time : float(Non mutable)
    status : OrderStatus (Mutable)
    price : float        (Non mutable)
    size : Integer       (Non mutable)
    exec_type : Exectype (Non mutable)
    exec_type_actual : Exectype (Mutable)
    """

    def __init__(self, creator_id, contract, creation_time, order_id, price, size, direction,
                 exec_type=Exectype.Market, expiration_time=float('inf'), status=OrderStatus.Created):
        super(Order, self).__init__()
        self.creator_id = creator_id
        self.contract = contract
        self.m_orderId = order_id
        self.direction = direction
        self.status = status
        self.price = price
        self.size = size
        self.exec_type = exec_type
        self.exec_type_actual = exec_type
        if self.exec_type in [Exectype.Market]:
            if self.price is not None:
                raise Exception('Error: Market order should have price == None')
        elif self.direction is not Direction.Cancel:
            if self.exec_type in [Exectype.Stop, Exectype.Limit, Exectype.StopLimit, Exectype.Market]:
                assert (isinstance(self.price, numbers.Number))
            else:
                raise Exception("Only Market, Stop, StopLimit and Limit orders allowed: %s" % self.exec_type.name)
        else:
            self.debug("Order created correctly")

        # Cannot create expired order
        if expiration_time < creation_time:
            raise Exception('Cannot create order with expiration time = %f < %f = creation_time' % (expiration_time, creation_time))

        # Important moments in the life cycle of an order
        self.expiration_time = expiration_time
        self.creation_time = creation_time
        self.accept_time = None
        self.reject_time = None
        self.cancel_time = None
        self.complete_time = None

        self.size_remaining = size
        # If the order gets executed in chunks: [(time, price, size_executed)]
        self.trades = []

    def get_identifier(self):
        return "order"

    def get_price(self):
        return self.price

    def get_size_remaining(self):
        return self.size_remaining

    def format_str(self):
        accepted_time = str(self.accept_time)
        order_id = str(self.m_orderId)
        direction = str(self.direction.name)
        contract = str(self.contract)
        price = str(self.price)
        volume = str(self.size)
        return "<" + ",".join([accepted_time, order_id, direction, contract, price, volume]) + ">"

    def mutate_exec_type(self, price_executed, size_executed):
        # TODO: this mutation could depend also on market conditions (liquidity, etc.)! (maybe it should)
        self.debug("mutate execution type of order %i" % self.m_orderId)
        map_conversion = {Exectype.Stop: Exectype.Market, Exectype.StopLimit: Exectype.Limit}
        map_operator = {Direction.Buy: operator.__le__, Direction.Sell: operator.__ge__}
        if map_operator[self.direction](price_executed, self.price):
            self.debug("Update exec_type from %s to %s" % (self.exec_type.name,
                                                             map_conversion[self.exec_type_actual].name))
            self.exec_type_actual = map_conversion[self.exec_type_actual]
            return True
        else:
            return False

    def get_expiration_time(self):
        return self.expiration_time

    def get_exec_type(self):
        return self.exec_type_actual

    def get_status(self):
        return self.status

    def complete(self, current_time):
        self.complete_time = current_time
        self.status = OrderStatus.Complete

    def cancel(self, current_time):
        self.cancel_time = current_time
        self.status = OrderStatus.Canceled
        return self.status

    def reject(self, current_time):
        self.reject_time = current_time
        self.status = OrderStatus.Rejected
        return self.status

    def expired(self):
        self.status = OrderStatus.Expired
        return self

    def accept(self, current_time):
        self.debug("Accepting order at time %f" % current_time)
        self.accept_time = current_time
        self.status = OrderStatus.Accepted
        return self.status

    def execute_order(self, execution_time, price_executed, size_executed):
        """
        It models the execution of a transaction. Tracks the internal state of the order
        Returns number of contracts executed
        :return: Integer
        """
        self.debug("Executing order at time %f" % execution_time)
        assert (size_executed <= self.size_remaining)
        self.size_remaining -= size_executed
        self.trades.append((execution_time, price_executed, size_executed))
        if self.size_remaining > 0:
            self.status = OrderStatus.Partial
        else:
            self.debug("Completed order (%s). Trades = %s" % (self.format_str(), str(self.trades)))
            self.complete(execution_time)
        return self.size_remaining

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        """
        Orders are equal only when they have same id
        :param other: Order
        :return: bool
        """
        return self.m_orderId == other.m_orderId

    def __str__(self):
        repr = self.__repr__()
        return repr

    def __repr__(self):
        repr = self.__dict__.copy()
        return str(repr)

    def __gt__(self, other):
        return not self.__lt__(other)

    def __lt__(self, other):
        """
        Definition of order relationship between orders. Assume smallest => highest priority
        :param other: Order
        :return: bool
        """
        assert (self.direction == other.direction)
        # TODO: Stop and StopLimit implementations: each time a trade executes, log exec price & update the Stop* orders

        # Warning about missing implementation
        not_implemented_1 = (self.get_exec_type() not in [Exectype.Limit, Exectype.Market])
        not_implemented_2 = (other.get_exec_type() not in [Exectype.Limit, Exectype.Market])
        if not_implemented_1 or not_implemented_2:
            raise NotImplemented('Only Limit and Market')

        # self.debug("pasa aca")
        # Warning about non-orderability of Market vs. Limit orders
        different_1 = self.exec_type is Exectype.Market and other.exec_type is Exectype.Limit
        different_2 = self.exec_type is Exectype.Limit and other.exec_type is Exectype.Market
        if different_1 or different_2:
            raise Exception('Market orders and Limit orders are not orderable')

        # Both orders are Market
        if self.exec_type is Exectype.Market and other.exec_type is Exectype.Market:
            # we do not consider the case when both market orders have the same accept time (set arbitrarily)
            return self.accept_time < other.accept_time

        # Both orders are Limit
        map_operator = {
            'price': {Direction.Buy: operator.gt, Direction.Sell: operator.lt},
            'accept_time': {Direction.Buy: operator.lt, Direction.Sell: operator.lt},
            'size': {Direction.Buy: operator.gt, Direction.Sell: operator.gt}
        }
        levels_importance = ['price', 'accept_time', 'size']
        if getattr(self, levels_importance[0]) == getattr(other, levels_importance[0]):
            if self.size == other.size:
                assert (self.accept_time is not None and other.accept_time is not None)
                return map_operator[levels_importance[2]][self.direction](getattr(self, levels_importance[2]),
                                                                          getattr(other, levels_importance[2]))
            else:
                return map_operator[levels_importance[1]][self.direction](getattr(self, levels_importance[1]),
                                                                          getattr(other, levels_importance[1]))
        else:
            return map_operator[levels_importance[0]][self.direction](getattr(self, levels_importance[0]),
                                                                      getattr(other, levels_importance[0]))
