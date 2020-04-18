import numpy as np
from src.strategies.strategy import Strategy
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.messages.for_orderbook import MessageForOrderbook
from src.exchange.messages.for_agent import MessageForAgent
from src.exchange.notifications.ob_notification import OBNotification
from src.exchange.notifications.order_status_notification import OrderStatusNotification
from src.exchange.orders.order_utils import Direction
from src.utils.debug import Debug


class StochasticStrategy6(Strategy, Debug):
    def __init__(self, agent, identifier, wakeup_distribution, cancellation_timeout,
                 direction, price_distribution, size_distribution, initial_cash, max_orders,
                 contract, exec_type, end_time):
        super(StochasticStrategy6, self).__init__(agent)
        self.identifier = identifier
        self.end_time = end_time

        # TODO
        self.max_orders = max_orders
        self.remaining_cash = initial_cash
        self.orders_completed_and_considered = {}

        self.cancellation_timeout = cancellation_timeout
        self.wakeup_distribution = lambda: np.round(wakeup_distribution(), 2)
        self.price_distribution = price_distribution
        self.size_distribution = size_distribution

        self.next_wakeup_time = self.wakeup_distribution()
        self.debug("Initialize next_wakeup_time = %f" % self.next_wakeup_time)
        self.time_advance = self.next_wakeup_time

        self.orders_sent = []   # order_id of each order sent
        self.cancellation_time_for_orders = []   # heap[(cancellation_time, order_id)]
        self.next_order = None

        self.direction = direction
        self.contract = contract
        self.exec_type = exec_type

    def get_remaining_cash(self):
        return self.remaining_cash

    def get_price(self, t):
        new_price = np.round(self.price_distribution(t)(), 2)
        self.debug("Price = %f" % new_price)
        return new_price

    def get_size(self, t):
        new_size = np.round(self.size_distribution(t)(), 2)
        self.debug("Size = %f" % new_size)
        return new_size

    def output_function(self, current_time, elapsed):
        output = {}
        for output_port in self.get_devs_model().output_ports:
            if output_port == 'out_order':
                send, order = self.get_next_order(current_time, elapsed)
                if send is True:
                    self.debug('Send order %i' % order.m_orderId)
                    self.debug("%f %f" % (current_time, elapsed))
                    output[output_port] = MessageForOrderbook(agent=self.get_devs_model().identifier,
                                                              time_sent=current_time + elapsed,
                                                              value=order)
                    self.next_order = None
            else:
                raise Exception()
        return output

    def get_next_order(self, current_time, elapsed):
        if self.next_order is None:
            return False, None
        else:
            return True, self.next_order

    def process_in_next(self, current_time, elapsed, message):
        self.debug("process_in_next")
        if current_time + elapsed >= self.end_time or current_time + elapsed > self.next_wakeup_time:
            return float('inf')
        return self.next_wakeup_time - current_time - elapsed

    def update_order_notification(self, notification):
        self.debug("update_order_notification")
        super(StochasticStrategy6, self).update_strategy_orders_status(notification)

        for order in notification.get_completed():
            if order.m_orderId not in self.orders_completed_and_considered:
                self.orders_completed_and_considered[order.m_orderId] = True
                # TODO: use only as confirmation.
                # if order.direction == Direction.Buy:
                #     self.remaining_cash -= order.price * order.size
                # else:
                #     self.remaining_cash += order.price * order.size
        # Nothing
        return None

    def process_in_notify_order(self, current_time, elapsed, message):
        self.debug("process_in_notify_order")
        if current_time + elapsed >= self.end_time or current_time + elapsed > self.next_wakeup_time:
            return float('inf')

        assert (isinstance(message.value, OrderStatusNotification))
        if isinstance(message, MessageForAgent):
            notification = message.value
            assert (isinstance(notification, OBNotification))
            self.update_order_notification(notification)

        return self.next_wakeup_time - current_time - elapsed

    def process_internal(self, current_time, elapsed):
        self.debug("process_internal")

        # TODO: standarize this to all transitions (internal and external)
        if current_time + elapsed >= self.end_time or current_time + elapsed > self.next_wakeup_time:
            return float('inf')

        size = self.get_size(current_time + elapsed)
        price = self.get_price(current_time + elapsed)

        # Propose wake up time. If there is a cancellation before, first cancel and then propose again
        next_order_wakeup_time = current_time + elapsed + self.wakeup_distribution()
        self.debug('setea next wakeup = %f' % next_order_wakeup_time)
        self.debug("%f %f" % (current_time, elapsed))

        # Finish: RUN OUT OF CASH OR RUN OUT OF TIME
        if (self.direction == Direction.Buy or self.direction == 1) and self.remaining_cash - price*size < 0:
            return float('inf')
        elif next_order_wakeup_time > self.end_time:
            return float('inf')
        elif len(self.orders_sent) >= self.max_orders:
            return float('inf')
        else:
            self.next_wakeup_time = next_order_wakeup_time
            self.debug("Wakeup (1) = %f, current=%f, elapsed=%f" % (self.next_wakeup_time, current_time, elapsed))
            next_id = np.random.randint(0, 1000)
            self.debug("Creating order %i at t=%f" % (next_id, current_time + elapsed))
            self.next_order = OrderCreator.create_order_from_dict({
                'contract': self.contract, 'creator_id': self.identifier,
                'order_id': next_id,
                'price': price, 'size': size,
                'direction': self.direction, 'exec_type': self.exec_type,
                'creation_time': current_time,
                # Option 1: set expiration time for automatic cancellations
                'expiration_time': current_time + elapsed + self.cancellation_timeout
            })

            if self.next_order.direction in [Direction.Buy, 1]:
                self.remaining_cash -= self.next_order.price * self.next_order.size
            elif self.next_order.direction in [Direction.Sell, -1]:
                self.remaining_cash += self.next_order.price * self.next_order.size
            else:
                raise Exception()

            # Important
            self.orders_sent.append(self.next_order.m_orderId)
            return self.next_wakeup_time - current_time - elapsed




