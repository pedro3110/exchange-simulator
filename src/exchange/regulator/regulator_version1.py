from pypdevs.DEVS import AtomicDEVS
from src.utils.debug import Debug
from src.exchange.messages.for_orderbook import MessageForOrderbook
from src.exchange.messages.for_journal import MessageForJournal
from src.exchange.messages.for_agent import MessageForAgent
from src.utils.rounding import assert_equals_rounded, assert_leq_rounded, eq_rounded
from src.utils.decorators import approximating_time_advance
import heapq


class BasicRegulatorVersion1(AtomicDEVS, Debug):
    """
    Has a specific connection with each orderbook & forwards messages intelligently
    Has a mapping order => agent, and only allows cancelling order send by same agent (or else, reject the order)
    """
    def __init__(self, market, identifier, current_time, remaining, input_ports, contract_port_map, agents_delay_map):
        AtomicDEVS.__init__(self, identifier)
        self.market = market
        self.identifier = identifier

        self.last_current_time = 0.0
        self.time_advance = float('inf')

        self.last_transition = None  # [internal, external]
        self.last_elapsed = 0.0

        # Ports corresponding to orderbooks
        self.contract_port_map = contract_port_map
        for port_name in input_ports:
            setattr(self, port_name, self.addInPort(port_name))
        for contract, port_name in contract_port_map.items():
            setattr(self, port_name, self.addOutPort(port_name))

        ports_map = {contract: getattr(self, port_name) for contract, port_name in contract_port_map.items()}
        self.strategy = RegulatorStrategy(self, identifier, agents_delay_map, ports_map)

    def get_identifier(self):
        return self.identifier

    @approximating_time_advance
    def get_elapsed(self):
        return self.elapsed

    @approximating_time_advance
    def get_current_time(self):
        return self.last_current_time

    def timeAdvance(self):
        self.debug("(clock) time advance: %f" % self.get_time_advance())
        return self.get_time_advance()

    @approximating_time_advance
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
        self.debug("====================> Internal transition (%f, %f, %f, %f)" % (
        self.get_current_time(), self.get_time_advance(), elapsed, self.get_current_time() + elapsed))

        ta = self.strategy.process_internal(self.get_current_time(), elapsed)
        # Updates
        self.time_advance = ta
        self.last_transition = 'internal'
        self.last_elapsed = ta
        self.last_current_time += elapsed

        self.debug("(intTransition) Update time_advance=%f, current_time=%f, last_elapsed=%f" % (
        self.time_advance, self.last_current_time, self.last_elapsed))
        return self.state

    def extTransition(self, inputs):
        elapsed = self.get_elapsed()
        self.debug("====================> External Transition (%f, %f, %f)" % (
        self.get_current_time(), elapsed, self.get_current_time() + elapsed))
        self.last_transition = 'external'

        map_method = {'in_order': self.strategy.process_in_order}
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


class RegulatorStrategy(Debug):
    def __init__(self, agent, identifier, agents_delay_map, output_ports_map):
        self.agent = agent
        self.identifier = identifier + '_strategy'
        self.agents_delay_map = agents_delay_map
        self.output_ports_map = output_ports_map

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
        self.debug("%f, %f, %f" % (message.time_sent, current_time, elapsed))

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
        self.debug("%s" % message)
        if isinstance(message, MessageForOrderbook):
            return self.process_input_message_for_orderbook(current_time, elapsed, message)
        elif isinstance(message, MessageForJournal):
            raise NotImplemented()
        elif isinstance(message, MessageForAgent):
            raise NotImplemented()
        else:
            raise Exception('Not implemented')
