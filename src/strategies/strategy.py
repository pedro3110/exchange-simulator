from src.exchange.orders.order_utils import OrderStatus
from src.utils.debug import Debug


class Strategy(Debug):
    """
    Every strategy should respect this interface
    Life flow of an order (cancel orders have same id as original order but with different Direction
    (CANCEL instead of BUY/SELL).
                                       | partial
                                       | complete
                                       | rejected
                                       | canceled
               pending accept ---------                  | canceled
              | (BUY/SELL)             | accepted --------
    . created                                            | complete
              |                 | rejected               | partial
               pending canceled
                (CANCEL)        | complete
                                | accepted -------- complete
    """

    def __init__(self, devs_model):
        super(Strategy, self).__init__()
        self.devs_model = devs_model
        self.identifier = devs_model.get_identifier() + '_strategy'

        # Status of strategy execution
        self.active = False
        # If not None, the output function will emit the order
        self.next_order = None

        @property
        def orders_sent(self):
            raise NotImplementedError

        # Enqueued to be sent right away
        self.orders_to_send = {}    # USED BY SUBCLASS
        self.orders_to_cancel = {}  # USED BY SUBCLASS
        # Orders processed by market (and the agent received the corresponding notify order)
        # Pending response
        self.orders_pending_accept = {}   # BID/ASK orders
        self.orders_pending_cancel = {}   # CANCEL orders (corresponding to some sent order)
        # With response
        self.orders_rejected = {}
        self.orders_accepted = {}
        self.orders_completed = {}
        # self.orders_canceled = {}
        self.orders_partial_completed = {}

    def get_identifier(self):
        return self.identifier

    def get_number_of_incomplete_orders(self):
        return len(self.orders_pending_accept) + len(self.orders_pending_cancel) + len(self.orders_accepted)

    def get_orders_pending_accept(self):
        return [order_id for order_id, _ in self.orders_pending_accept.items()]

    def get_accepted(self):
        return [order_id for order_id, _ in self.orders_accepted.items()]

    def get_rejected(self):
        return [order_id for order_id, _ in self.orders_rejected.items()]

    def get_completed(self):
        return [order_id for order_id, _ in self.orders_completed.items()]

    def get_partial_completed(self):
        return [order_id for order_id, _ in self.orders_partial_completed.items()]

    def get_orders_status(self):
        map_order_status = {}
        for order_id in self.get_orders_pending_accept():
            map_order_status[order_id] = OrderStatus.Created
        for order_id in self.get_accepted():
            map_order_status[order_id] = OrderStatus.Accepted
        for order_id in self.get_rejected():
            map_order_status[order_id] = OrderStatus.Rejected
        for order_id in self.get_partial_completed():
            map_order_status[order_id] = OrderStatus.Partial
        for order_id in self.get_completed():
            map_order_status[order_id] = OrderStatus.Complete
        # Answer
        return map_order_status

    # def get_canceled(self):
    #     return [order_id for order_id, _ in self.orders_canceled.items()]

    def start(self):
        assert(not self.active)
        self.active = True
        return 0

    def stop(self):
        assert(self.active is True)
        self.active = False
        return 0

    def get_devs_model(self):
        return self.devs_model

    def process_internal_transition(self):
        raise NotImplemented()

    def output_prepared(self, output_port):
        raise NotImplemented()

    def next_output_value(self, output_port):
        raise NotImplemented

    def update_rejected(self, orders):
        for order in orders:
            # Only update orders sent by me
            if order.m_orderId in self.orders_sent:
                self.debug("Update rejected: %i" % order.m_orderId)
                # assert(order.m_orderId in self.orders_pending_accept or order.m_orderId in self.orders_pending_cancel)
                # Update
                self.orders_rejected[order.m_orderId] = order
                if order.m_orderId in self.orders_pending_accept:
                    del self.orders_pending_accept[order.m_orderId]
                # pending to be canceled
                if order.m_orderId in self.orders_pending_cancel:
                    del self.orders_pending_cancel[order.m_orderId]
        return 0

    def update_completed(self, orders):
        """
        Remove order from accepted and pending_accepted
        :param orders:
        :return:
        """
        for order in orders:
            # Only update orders sent by me
            if order.m_orderId in self.orders_sent:
                # self.debug("Update completed: %i" % order.m_orderId)
                # Add as completed
                if order.m_orderId in self.orders_completed:
                    # TODO: maybe check if the message is exactly the same or if it has some modification
                    self.debug("Duplicated information")
                # Set as completed
                self.orders_completed[order.m_orderId] = order
                # Remove from the possible lists
                # pending to be accepted
                if order.m_orderId in self.orders_pending_accept:
                    del self.orders_pending_accept[order.m_orderId]
                # accepted but not complete
                if order.m_orderId in self.orders_accepted:
                    del self.orders_accepted[order.m_orderId]
                # pending to be canceled
                if order.m_orderId in self.orders_pending_cancel:
                    del self.orders_pending_cancel[order.m_orderId]
                # partial pending to complete
                if order.m_orderId in self.orders_partial_completed:
                    del self.orders_partial_completed[order.m_orderId]
        return 0

    def update_accepted(self, orders):
        for order in orders:
            # Only update orders sent by me (ALLOW PREVIOUS STATUS)
            if order.m_orderId in self.orders_sent:
                # Can receive messages from old updates
                # Update
                self.orders_accepted[order.m_orderId] = order
                if order.m_orderId in self.orders_pending_accept:
                    del self.orders_pending_accept[order.m_orderId]
                # pending to be canceled
                if order.m_orderId in self.orders_pending_cancel:
                    del self.orders_pending_cancel[order.m_orderId]
        return 0

    def update_partial_completed(self, orders):
        for order in orders:
            if order.m_orderId in self.orders_sent:
                #  Move to accepted orders if necessary
                self.orders_partial_completed[order.m_orderId] = order
                # Update
                if order.m_orderId in self.orders_pending_accept:
                    del self.orders_pending_accept[order.m_orderId]
                if order.m_orderId in self.orders_accepted:
                    del self.orders_accepted[order.m_orderId]
        return 0

    def update_strategy_orders_status(self, ob_notification):
        self.debug("update_strategy_orders_status")
        self.update_accepted(ob_notification.get_accepted())
        self.update_partial_completed(ob_notification.get_partial_completed())  # must execute BEFORE update_completed
        self.update_completed(ob_notification.get_completed())
        self.update_rejected(ob_notification.get_rejected())
        # TODO: return updates
        return 0
