from pypdevs.DEVS import AtomicDEVS
from src.utils.debug import Debug
from src.exchange.notifications.ob_notification import OBNotification
from src.exchange.messages.for_journal import MessageForJournal
from src.exchange.notifications.market_status_notification import MarketStatusNotification
from src.exchange.notifications.order_status_notification import OrderStatusNotification
from src.exchange.messages.for_agent import MessageForAgent
from src.utils.rounding import eq_rounded
import heapq


class JournalVersion1(AtomicDEVS, Debug):
    """
    Journal DEVS Atomic model. It keeps track of the latest updates in orderbooks and market state, and transmits some
    of this information to the agent that interact with the market. This is a service that the journal provides to
    the agent that have a subscription to the journal
    """
    def __init__(self, market, identifier, current_time, remaining, journal_input_ports,
                 journal_output_ports):
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
        self.strategy = JournalStrategy(self, identifier+'_strategy', output_ports_map)


    def get_identifier(self):
        return self.identifier

    def get_elapsed(self):
        return self.elapsed

    def get_current_time(self):
        return self.last_current_time

    def timeAdvance(self):
        self.debug("(clock) time advance: %f" % self.get_time_advance())
        return self.get_time_advance()

    def get_time_advance(self):
        return self.time_advance

    def outputFnc(self):
        elapsed = self.get_time_advance()
        self.debug("last_elapsed=%f elapsed=%f" % (self.last_elapsed, elapsed))
        self.debug("====================> Output function (%f, %f, %f)" % (
        self.get_current_time(), self.get_time_advance(), self.get_current_time() + elapsed))

        output = self.strategy.output_function(self.last_current_time, elapsed)
        return output

    def intTransition(self):
        elapsed = self.get_time_advance()
        self.debug("last_elapsed=%f elapsed=%f" % (self.last_elapsed, elapsed))
        self.debug("====================> Internal transition (%f, %f, %f, %f)" % (self.get_current_time(), self.get_time_advance(), elapsed, self.get_current_time() + elapsed))

        ta = self.strategy.process_internal(self.get_current_time(), elapsed)
        # Updates
        self.time_advance = ta
        self.last_transition = 'internal'
        self.last_elapsed = ta
        self.last_current_time += elapsed

        self.debug("(intTransition) Update time_advance=%f, current_time=%f, last_elapsed=%f" % (self.time_advance, self.last_current_time, self.last_elapsed))
        return self.state

    def extTransition(self, inputs):
        elapsed = self.get_elapsed()
        self.debug("====================> External Transition (%f, %f, %f)" % (self.get_current_time(), elapsed, self.get_current_time() + elapsed))
        self.last_transition = 'external'

        map_method = {'in_orderbook': self.strategy.process_in_orderbook,
                      'in_agent': self.strategy.process_in_agent}
        assert (set(map_method.keys()).issubset(set([port.name for port in self.ports if port.is_input])))
        input_match = list(filter(lambda x: x.name in map_method.keys(), inputs.keys()))
        assert (len(input_match) == 1)
        message = inputs[input_match[0]]
        ta = map_method[input_match[0].name](self.get_current_time(), self.get_elapsed(), message)
        # Updates
        self.last_elapsed = ta
        self.time_advance = ta
        self.last_current_time += elapsed
        self.debug("(extTransition) Update time_advance = %f" % self.time_advance)
        return self.strategy


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

        self.ob_notifications = []
        self.next_messages_delivery = {output_port: [] for output_port in output_ports_map}  # output_port => [message]

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
                    # self.debug("ASDF %f %f %f" % (current_time, elapsed, next_message.wakeup_time))
                    external_message = next_message.message
                    external_message.set_time_sent(current_time + elapsed)
                    # Output through right port
                    output[self.output_ports_map[output_port]] = external_message

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

                # Get min wakeup time
                # smallest_wakeup_time = float('inf')
                # for out_port in ['out_next', 'out_notify_order']:
                #     if len(self.next_messages_delivery[out_port]) > 0:
                #         smallest_tmp = heapq.nsmallest(1, self.next_messages_delivery[out_port])[0].wakeup_time
                #         smallest_wakeup_time = min(smallest_wakeup_time, smallest_tmp)
                # self.debug("Wait time = %f" % smallest_wakeup_time)

                # Log notification of orders
                self.debug("%s" % str([len(m.message.value.get_accepted()) for m in self.next_messages_delivery['out_notify_order']]))
                self.debug("%s" % str([len(m.message.value.get_completed()) for m in self.next_messages_delivery['out_notify_order']]))
                return 0
            else:
                raise Exception('Journal message must contain an OBNotification')
        else:
            raise Exception()