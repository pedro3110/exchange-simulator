from pypdevs.DEVS import AtomicDEVS
from src.utils.debug import Debug
from src.exchange.notifications.ob_notification import OBNotification
from src.exchange.messages.for_journal import MessageForJournal
from src.exchange.notifications.market_status_notification import MarketStatusNotification
from src.exchange.notifications.order_status_notification import OrderStatusNotification
from src.exchange.messages.for_agent import MessageForAgent
from src.exchange.base_journal import JournalBase
from src.utils.rounding import eq_rounded
import heapq


class JournalVersion1(JournalBase, Debug):
    def __init__(self, market, identifier):
        AtomicDEVS.__init__(self, identifier)
        self.market = market
        self.identifier = identifier

        self.last_current_time = 0.0
        self.time_advance = float('inf')

        self.last_transition = None  # [internal, external]
        self.last_elapsed = 0.0

        self.in_agent = self.addInPort("in_agent")
        self.in_orderbook = self.addInPort("in_orderbook")

        self.out_next = self.addOutPort("out_next")
        self.out_notify_order = self.addOutPort("out_notify_order")
        output_ports_map = {
            'out_next': getattr(self, 'out_next'),
            'out_notify_order': getattr(self, 'out_notify_order')
        }
        strategy_params = {
            'identifier': identifier + '_strategy',
            'output_ports_map': output_ports_map
        }
        super(JournalVersion1, self).__init__(identifier+'_strategy', JournalStrategy, strategy_params)


class MessageToDeliver:
    def __init__(self, identifier, message, wakeup_time):
        self.identifier = identifier
        self.message = message
        self.wakeup_time = wakeup_time

    def __lt__(self, other):
        return self.wakeup_time < other.wakeup_time


class JournalStrategy(Debug):
    def __init__(self, agent, identifier, output_ports_map):
        super(JournalStrategy, self).__init__()
        self.agent = agent
        self.identifier = identifier
        self.output_ports_map = output_ports_map

        self.next_wakeup_time = float('inf')

        self.ob_notifications = []
        self.next_messages_delivery = {output_port: [] for output_port in output_ports_map}

        self.last_message_id = 0

    def get_identifier(self):
        return self.identifier

    def output_function(self, current_time, elapsed):
        output = {}
        for output_port in ['out_next', 'out_notify_order']:
            self.debug("Seach port %s" % output_port)
            self.debug("%s" % str(self.next_messages_delivery))
            messages = self.next_messages_delivery[output_port]
            if len(messages) > 0:
                next_message = heapq.heappop(messages)
                assert (current_time + elapsed <= next_message.wakeup_time)
                if eq_rounded(current_time + elapsed, next_message.wakeup_time):
                    self.debug("current_time + elapsed == next_message.wakeup_time")
                    external_message = next_message.message
                    external_message.set_time_sent(current_time + elapsed)
                    output[output_port] = external_message

                else:
                    self.debug("%f %f %f" % (current_time, elapsed, next_message.wakeup_time))
        self.debug("Emit output = %s" % str(output))
        return output

    def process_internal(self, current_time, elapsed):

        # TODO: wakeup every 5 seconds

        self.debug("process_internal")
        self.debug("%s" % str(self.next_messages_delivery))
        smallest_wakeup_time = float('inf')
        best_key = None
        for key in self.next_messages_delivery:
            messages = self.next_messages_delivery[key]
            if len(messages) > 0:
                wakeup_time = heapq.nsmallest(1, messages)[0].wakeup_time
                if wakeup_time < smallest_wakeup_time:
                    best_key = key
                    smallest_wakeup_time = wakeup_time
        if best_key is not None:
            self.debug("Enqueued message found")
            return smallest_wakeup_time - current_time - elapsed
        else:
            self.debug("Enqueued message not found")
            return float('inf')

    def process_in_agent(self, current_time, elapsed, message):
        raise NotImplemented()

    def process_in_next(self, current_time, elapsed, message):
        raise NotImplemented()

    def get_next_message_id(self):
        self.last_message_id += 1
        return self.last_message_id

    def process_in_orderbook(self, current_time, elapsed, message):
        self.debug("process_in_orderbook")
        self.debug("Current time = %f %f" % (current_time, elapsed))
        self.debug("Message time_sent = %f" % message.time_sent)
        if isinstance(message, MessageForJournal):
            if isinstance(message.value, OBNotification):
                ob_notification = message.value
                market_status_notification = MarketStatusNotification(
                    execution_information=ob_notification.get_ob_information()
                )
                wakeup_time = current_time+elapsed
                external_message1 = MessageForAgent(time_sent=wakeup_time, value=market_status_notification)
                internal_message = MessageToDeliver(self.get_next_message_id(), external_message1, wakeup_time)
                heapq.heappush(self.next_messages_delivery['out_next'], internal_message)

                # Port notify_order
                order_status_notification = OrderStatusNotification(
                    completed=ob_notification.get_completed(),
                    partial_completed=ob_notification.get_partial_completed(),
                    expired=ob_notification.get_expired(), accepted=ob_notification.get_accepted(),
                    rejected=ob_notification.get_rejected(), canceled=ob_notification.get_canceled(),
                    matched=ob_notification.get_matched()
                )
                external_message2 = MessageForAgent(time_sent=wakeup_time, value=order_status_notification)
                internal_message2 = MessageToDeliver(self.get_next_message_id(), external_message2, wakeup_time)
                heapq.heappush(self.next_messages_delivery['out_notify_order'], internal_message2)

                # Log notification of orders
                self.debug("%s" % str([len(m.message.value.get_accepted()) for m in self.next_messages_delivery['out_notify_order']]))
                self.debug("%s" % str([len(m.message.value.get_completed()) for m in self.next_messages_delivery['out_notify_order']]))
                return 0
            else:
                raise Exception('Journal message must contain an OBNotification')
        else:
            raise Exception()
