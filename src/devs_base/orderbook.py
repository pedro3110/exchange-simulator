from pypdevs.DEVS import AtomicDEVS
from src.system_components.helpers.orderbook.orderbook_state import OrderbookState
from src.utils.decorators.external_transition import updating_current_time_with_state
from src.utils.config import get_logger, log_files
logger = get_logger('orderbook', log_files['orderbook'])


class Orderbook(AtomicDEVS):
    """
    The OB is encharged of handling all buy / sell orders sent by the agent that want to interact with the market.
    The OB matches the orders according to certain rules (best price first + FIFO)
    The OB keeps track of the current time and regularly checks for expirations in the bid ask table
    """
    def __init__(self, identifier, contract, current_time, input_ports, output_ports,
                 remaining=float('inf'), delay_order=0.0, delay_notification=0.0):
        AtomicDEVS.__init__(self, identifier)
        self.identifier = identifier
        self.contract = contract
        self.state = OrderbookState(self, contract, current_time, remaining, delay_order, delay_notification)
        for port_name in input_ports:
            setattr(self, port_name, self.addInPort(port_name))
        for port_name in output_ports:
            setattr(self, port_name, self.addOutPort(port_name))
        logger.debug("Initialized orderbook. in_ports = %s | out_ports = %s" % (str(input_ports), str(output_ports)))

    def intTransition(self):
        """
        Update internal state considering:
            - The BidAsk Table has to match orders and inform the orders that were modified during the process
            -
        :return: OrderbookState
        """
        logger.debug("====================> Internal Transition (%f)" % self.state.current_time)
        self.state.remaining = self.state.process_internal_transition()
        if self.state.remaining != float('inf'):
            # Update current_time (for next time it wakes up; only when time advance is < inf)
            self.state.current_time += self.state.remaining
            logger.debug("Update next current_time = %f" % self.state.current_time)
        # Finish internal transition
        return self.state

    def timeAdvance(self):
        """
        Check regularly for expiration of orders.
        :return: OrderbookState
        """
        logger.debug("(clock) time advance: %f" % self.state.remaining)
        return self.state.remaining

    def outputFnc(self):
        """
        Notify { completed / canceled / partial / expired } orders
        :return: dict
        """
        logger.debug("====================> Output function (%f)" % self.state.current_time)
        output_ports = {port.name for port in self.ports if not port.is_input}
        map_portname_output = self.state.outputFnc(output_ports)
        output_messages = {
            next(iter(filter(lambda x: x.name is portname, self.ports)), None): message
            for portname, message in map_portname_output.items()
        }
        return output_messages

    @updating_current_time_with_state
    def extTransition(self, inputs):
        """
        Receive, validate and push new order to BidAsk table.
        Schedule internal transition to execute immediately, to update the table accordingly (matching orders).
        The order is Accepted/Rejected
        :param inputs:
        :return: OrderbookState
        """
        logger.debug("====================> External transition (%f)" % self.state.current_time)
        map_method = {
            'in_order': self.state.process_in_order
        }
        assert (set(map_method.keys()).issubset(set([port.name for port in self.ports if port.is_input])))
        input_match = list(filter(lambda x: x.name in map_method.keys(), inputs.keys()))
        if len(input_match) != 1:
            raise Exception('Not implemented: implemented only in_agent and in_orderbook')
        else:
            self.state.remaining = map_method[input_match[0].name](inputs[input_match[0]])
        return self.state
