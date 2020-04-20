import numpy as np
from src.strategies.strategy import Strategy
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.messages.for_orderbook import MessageForOrderbook
from src.utils.debug import Debug


class StochasticStrategy2(Strategy, Debug):
    def __init__(self, agent, identifier, wakeup_distribution, direction, price_distribution,
                 contract, exec_type, end_time):
        super(StochasticStrategy2, self).__init__(agent)
        self.identifier = identifier
        self.end_time = end_time

        self.wakeup_distribution = lambda: np.round(wakeup_distribution(), 2)
        self.price_distribution = lambda: np.round(price_distribution(), 2)

        self.next_wakeup_time = self.wakeup_distribution()
        self.time_advance = self.next_wakeup_time

        self.next_order = None

        self.direction = direction
        self.contract = contract
        self.exec_type = exec_type

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

    def process_in_notify_order(self, current_time, elapsed, message):
        return self.next_wakeup_time - current_time - elapsed

    def process_in_next(self, current_time, elapsed, message):
        return self.next_wakeup_time - current_time - elapsed


    def process_internal(self, current_time, elapsed):
        # I
        size = 5
        price = self.price_distribution()
        self.next_wakeup_time = current_time + elapsed + self.wakeup_distribution()

        next_id = np.random.randint(0, 1000)
        self.debug("Creating order %i at t=%f" % (next_id, current_time + elapsed))
        if self.next_wakeup_time > self.end_time:
            return float('inf')
        else:
            self.next_order = OrderCreator.create_order_from_dict({
                'contract': self.contract, 'creator_id': self.identifier,
                'order_id': next_id,
                'price': price, 'size': size,
                'direction': self.direction, 'exec_type': self.exec_type,
                'creation_time': current_time,
                'expiration_time': float('inf')
            })
            return self.next_wakeup_time - current_time - elapsed




