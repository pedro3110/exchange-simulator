from src.utils.debug import Debug
from src.utils.ifnonizer import ifnonizer
from src.exchange.orders.order_utils import OrderStatus


class LOBTableNotification(Debug):
    """
    Encode all information regarding the changes made in a Bid/Ask table after a new order arrival
    """
    def __init__(self,
                 completed=None, partial_completed=None, canceled=None,
                 accepted=None, rejected=None, expired=None,
                 matched=None):
        super(LOBTableNotification, self).__init__()
        # self.debug("Initializing new LOBTableNotification")
        self.completed = ifnonizer(completed, [])
        assert (all(x.get_status() in [OrderStatus.Complete, OrderStatus.Canceled] for x in self.completed))

        self.partial_completed = ifnonizer(partial_completed, [])
        assert (all(x.get_status() is OrderStatus.Partial for x in self.partial_completed))

        self.expired = ifnonizer(expired, [])
        assert (all(x.get_status() is OrderStatus.Expired for x in self.expired))

        self.canceled = ifnonizer(canceled, [])
        assert (all(x.get_status() is OrderStatus.Canceled for x in self.canceled))

        self.accepted = ifnonizer(accepted, [])
        assert (all(x.get_status() is OrderStatus.Accepted for x in self.accepted))

        self.rejected = ifnonizer(rejected, [])
        assert (all(x.get_status() is OrderStatus.Rejected for x in self.rejected))

        # TODO: define if this is needed
        self.matched = ifnonizer(matched, [])

    def get_identifier(self):
        return "lob_notification"

    def get_order_ids(self):
        return list(map(lambda x: x.m_orderId, self.completed + self.partial_completed + self.expired +
                        self.accepted + self.rejected + self.canceled))

    def append(self, completed=None, partial_completed=None, expired=None, canceled=None,
               accepted=None, rejected=None, matched=None):
        self.completed += ifnonizer(completed, [])
        assert(all(x.get_status() in [OrderStatus.Complete, OrderStatus.Canceled] for x in self.completed))

        self.partial_completed += ifnonizer(partial_completed, [])
        assert (all(x.get_status() is OrderStatus.Partial for x in self.partial_completed))

        self.expired += ifnonizer(expired, [])
        assert (all(x.get_status() is OrderStatus.Expired for x in self.expired))

        self.canceled += ifnonizer(canceled, [])
        assert (all(x.get_status() is OrderStatus.Canceled for x in self.canceled))

        self.accepted += ifnonizer(accepted, [])
        assert (all(x.get_status() is OrderStatus.Accepted for x in self.accepted))

        self.rejected += ifnonizer(rejected, [])
        assert (all(x.get_status() is OrderStatus.Rejected for x in self.rejected))

        self.matched += ifnonizer(matched, [])

        return self

    def _get_group_of_orders(self, status):
        """
        Auxiliary method
        :param status:
        :return:
        """
        map_status_group = {
            OrderStatus.Complete: self.completed,
            OrderStatus.Partial: self.partial_completed,
            OrderStatus.Expired: self.expired,
            OrderStatus.Canceled: self.canceled,
            OrderStatus.Accepted: self.accepted,
            OrderStatus.Rejected: self.rejected
        }
        return map_status_group[status]

    def fill_with_orders(self, orders):
        for order in orders:
            self._get_group_of_orders(order.get_status()).append(order)
        return self


    def _merge_partial(self, other):
        """
        Auxiliary method
        :param other:
        :return:
        """
        assert(isinstance(other, LOBTableNotification))
        self.debug("Merging partials")
        new_partial_completed = self.partial_completed + other.partial_completed
        assert(len(list(set(new_partial_completed))) == len(new_partial_completed))
        other_completed_ids = [order.m_orderId for order in other.completed]
        new_partial_completed = [order for order in new_partial_completed if order.m_orderId not in other_completed_ids]
        self.debug(new_partial_completed)
        return new_partial_completed

    def extend(self, other):
        """
        Consider removing orderse that are Partial in self and are Completed in other
        :param other: Order
        :return: LOBTableNotification
        """
        assert(isinstance(other, LOBTableNotification))
        # partials => completed
        new_partial_completed = self._merge_partial(other)
        new_accepted = other.accepted
        new_completed = other.completed
        self.append(completed=new_completed, partial_completed=new_partial_completed, accepted=new_accepted,
                    expired=other.expired, canceled=other.canceled, rejected=other.rejected)
        return self

    def __str__(self):
        repr = self.__repr__()
        return repr

    def __repr__(self):
        repr = self.__dict__.copy()
        return str(repr)
