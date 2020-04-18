from src.strategies.strategy import Strategy
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.messages.for_orderbook import MessageForOrderbook
from src.exchange.messages.for_agent import MessageForAgent
from src.exchange.notifications.ob_notification import OBNotification
from src.utils.debug import Debug
from src.utils.rounding import assert_equals_rounded


class ReplayVersion3Strategy(Strategy, Debug):
    def __init__(self, agent, identifier, history):
        super(ReplayVersion3Strategy, self).__init__(agent)
        self.history = history
        self.identifier = identifier

        self.n_orders = self.history.shape[0]
        self.n_order_to_send = 1
        self.orders_sent = []

        # Initialization
        self.next_order = self.prepare_order()
        self.last_waiting_time = self.next_order.creation_time
        self.next_wakeup_time = self.last_waiting_time
        self.prepared_to_send_next_order = False

    def get_identifier(self):
        return self.identifier

    def prepare_order(self):
        row = self.history.iloc[self.n_order_to_send - 1].copy()
        row['creator_id'] = self.get_devs_model().identifier
        next_order = OrderCreator.create_order_from_dict(row)
        return next_order

    def output_function(self, current_time, elapsed):
        output = {}
        for output_port in self.get_devs_model().output_ports:
            if output_port == 'out_order':
                send, order = self.get_next_order(current_time, elapsed)
                if send is True:
                    self.debug('Send order %i' % order.m_orderId)
                    output[output_port] = MessageForOrderbook(agent=self.get_devs_model().identifier,
                                                              time_sent=current_time + elapsed,
                                                              value=order)
            else:
                raise Exception()
        return output

    def process_internal(self, current_time, elapsed):
        # If already emitted output => get next order!
        self.debug("next_wakeup = %f, curr = %f, elapsed = %f" % (self.next_wakeup_time, current_time, elapsed))
        if not (current_time + elapsed, self.next_wakeup_time):
            self.debug("self.next_wakeup_time != self.get_current_time() + elapsed")
            assert(current_time + elapsed < self.next_wakeup_time)
            return self.next_wakeup_time - current_time - elapsed
        else:
            assert(current_time + elapsed == self.next_wakeup_time)
            if self.n_order_to_send <= self.n_orders:
                assert(self.prepared_to_send_next_order)
                self.debug("Prepared to send next order == True")

                self.next_order = self.prepare_order()
                self.prepared_to_send_next_order = False

                waiting_time = self.next_order.creation_time - current_time - elapsed
                self.next_wakeup_time = self.next_order.creation_time

                self.debug('waiting time=%f, next_wakeup_time=%f' % (waiting_time, self.next_wakeup_time))
                return waiting_time
            else:
                self.debug('wait = inf')
                self.next_wakeup_time = float('inf')
                return float('inf')

    def process_in_next(self, current_time, elapsed, message):
        self.debug("process_in_next")
        self.debug("%f, %f, %f" % (current_time, elapsed, message.time_sent))
        assert_equals_rounded(message.time_sent, current_time + elapsed)
        if isinstance(message, MessageForAgent):
            return self.next_wakeup_time - current_time - elapsed
        else:
            raise Exception('Not implemented')

    def process_in_notify_order(self, current_time, elapsed, message):
        self.debug("process_in_notify_order")
        if isinstance(message, MessageForAgent):
            notification = message.value
            assert (isinstance(notification, OBNotification))
            self.debug("Message received at %f" % message.time_sent)
            self.update_strategy_orders_status(notification)
            self.debug("self.next_wakeup_time = %f" % self.next_wakeup_time)
            return self.next_wakeup_time - current_time - elapsed
        else:
            raise Exception('Not implemented')

    def get_next_order(self, current_time, elapsed):
        self.debug("get_next_order %f %f %f" % (current_time, elapsed, self.next_wakeup_time))
        self.debug("%s" % self.next_order)
        send_output = self.next_order is not None and current_time + elapsed == self.next_wakeup_time
        if send_output:
            self.debug("Order emitted: %s" % self.next_order)
            next_order = self.next_order
            self.orders_sent.append(next_order.m_orderId)
            self.orders_pending_accept[next_order.m_orderId] = next_order
            self.n_order_to_send += 1
            self.next_order = None
            self.prepared_to_send_next_order = True
            return True, next_order
        else:
            return False, None

    def get_next_n_order_to_send(self):
        return self.n_order_to_send

    def get_n_orders(self):
        return self.n_orders
