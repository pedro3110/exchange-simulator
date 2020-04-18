from src.exchange.orders.order_utils import OrderStatus, Direction, Exectype
from src.utils.debug import Debug
import numpy as np


class OrderChecker(Debug):
    """
    Check and update order's status
    Methods
    -------
    checked_classified : Order
        modifies the state of the order according to certain classification rules
    check_expired : Order
        modifies the state of the order into Expired if it has expired (in relation to the current time of simulation)
    """
    def __init__(self, table, queue_observer):
        super(OrderChecker, self).__init__()
        self.table = table
        self.queue_observer = queue_observer
        self.tick_size_decimals = 7

    def get_identifier(self):
        return "order_checker"

    def checked_classified(self, order):
        """
        Updates the status of order. It can be Created, Rejected, Expired, Accepted
        :param order: Order
        :return: Order
        """
        assert (order.get_status() is OrderStatus.Created)
        assert (order.direction is not Direction.Cancel)
        if order.exec_type not in [Exectype.Market, Exectype.Stop]:
            assert (order.price is not None)
            check_left = np.round(order.price / self.table.tick_size, self.tick_size_decimals)
            check_right = np.round(order.price / self.table.tick_size, self.tick_size_decimals)
            assert check_left == check_right
        # Check expiration
        order = self.checked_expired(order)
        if order.get_status() is OrderStatus.Expired:
            self.debug("Order expired: order.reject()")
            order.reject(self.table.get_current_time())
        else:
            if not self.table.allow_duplicated_ids and order.m_orderId in self.queue_observer.get_order_ids():
                self.debug("Order implies duplicated id: order.reject()")
                order.reject(self.table.get_current_time())
            else:
                self.debug("Order can be accepted: order.accept()")
                order.accept(self.table.get_current_time())
        return order

    def checked_expired(self, order):
        """
        Update order's state if it has already expired
        :param order: Order
        :return: Order
        """
        exp_time = order.get_expiration_time()
        curr_time = self.table.current_time
        # self.debug("Check %i expiration: exp(%f) vs. curr(%f)" % (order.m_orderId, exp_time, curr_time))
        if curr_time >= exp_time:
            self.debug("Order %i has expired" % order.m_orderId)
            order.expired()
        return order
