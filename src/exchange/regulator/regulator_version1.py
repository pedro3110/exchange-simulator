from pypdevs.DEVS import AtomicDEVS
from src.utils.debug import Debug
from src.exchange.messages.for_orderbook import MessageForOrderbook
from src.exchange.messages.for_journal import MessageForJournal
from src.exchange.messages.for_agent import MessageForAgent
from src.utils.rounding import assert_equals_rounded, assert_leq_rounded, eq_rounded
from src.utils.decorators import approximating_time_advance
from src.exchange.base_regulator import RegulatorBase
import heapq


class BasicRegulatorVersion1(RegulatorBase, Debug):
    def __init__(self, market, identifier, input_ports, contract_port_map, agents_delay_map):

        self.market = market
        # self.identifier = identifier

        self.last_current_time = 0.0
        self.time_advance = float('inf')

        self.last_transition = None
        self.last_elapsed = 0.0
        strategy_params = {
            'identifier': identifier,
            'agents_delay_map': agents_delay_map,
            'output_ports_map': contract_port_map
        }
        super(BasicRegulatorVersion1, self).__init__(identifier, RegulatorStrategy, strategy_params,
                                                     input_ports, contract_port_map)


class MessageToDeliver:
    def __init__(self, identifier, message, wakeup_time):
        self.identifier = identifier
        self.message = message
        self.wakeup_time = wakeup_time

    def __lt__(self, other):
        return self.wakeup_time < other.wakeup_time


class RegulatorStrategy(Debug):
    def __init__(self, agent, identifier, agents_delay_map, output_ports_map):
        self.agent = agent
        self.identifier = identifier + '_strategy'
        self.agents_delay_map = agents_delay_map
        self.output_ports_map = output_ports_map

        self.next_wakeup_time = float('inf')

        self.next_messages_delivery = {output_port: [] for output_port in output_ports_map}  # output_port => [message]
        self.map_order_agent = {}  # order_id => agent_id

        self.messages_to_reject = []  # TODO: implement!
        self.last_message_id = 0

    def get_identifier(self):
        return self.identifier

    def get_next_message_id(self):
        self.last_message_id += 1
        return self.last_message_id

    def output_function(self, current_time, elapsed):
        output = {}
        for output_port in self.output_ports_map.keys():
            self.debug("Seach port %s" % output_port)
            self.debug("%s" % str(self.next_messages_delivery))
            messages = self.next_messages_delivery[output_port]
            if len(messages) > 0:
                next_message = heapq.heappop(messages)
                assert_leq_rounded(current_time + elapsed, next_message.wakeup_time)
                self.debug("Check current_time + elapsed == next_message.wakup_time")
                if eq_rounded(current_time + elapsed, next_message.wakeup_time):
                    # self.debug("current_time + elapsed == next_message.wakeup_time")
                    external_message = next_message.message
                    external_message.set_time_sent(current_time + elapsed)
                    # Output through right port
                    output[self.output_ports_map[output_port]] = external_message
                else:
                    self.debug("%f %f %f" % (current_time, elapsed, next_message.wakeup_time))
        self.debug("Emit output = %s" % str(output))
        return output


    def prepare_message_for_agent(self):
        raise NotImplemented()

    def prepare_message_for_orderbook(self, message, wakeup_time):
        new_internal_message = MessageToDeliver(identifier=self.get_next_message_id(),
                                                message=message, wakeup_time=wakeup_time)
        return new_internal_message

    def process_input_message_for_orderbook(self, current_time, elapsed, message):
        assert_equals_rounded(message.time_sent, current_time + elapsed)
        if isinstance(message, MessageForOrderbook):
            wakeup_time = message.time_sent + self.agents_delay_map[message.agent]
            new_internal_message = self.prepare_message_for_orderbook(message, wakeup_time)
            message_key = message.value.contract
            heapq.heappush(self.next_messages_delivery[message_key], new_internal_message)
            smallest = heapq.nsmallest(1, self.next_messages_delivery[message_key])[0]
            waiting_time = smallest.wakeup_time - current_time - elapsed
            self.debug("Waiting time = %f" % waiting_time)
            self.debug("%s" % str(self.next_messages_delivery))
            return waiting_time
        else:
            raise Exception()

    def process_internal(self, current_time, elapsed):
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


    def process_in_order(self, current_time, elapsed, message):
        self.debug("process_in_order")
        if isinstance(message, MessageForOrderbook):
            return self.process_input_message_for_orderbook(current_time, elapsed, message)
        elif isinstance(message, MessageForJournal):
            raise NotImplemented()
        elif isinstance(message, MessageForAgent):
            raise NotImplemented()
        else:
            raise Exception('Not implemented')
