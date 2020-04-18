from pypdevs.DEVS import AtomicDEVS
from src.utils.decorators.external_transition import updating_current_time_with_manager
from src.utils.config import get_logger, log_files
logger = get_logger('journal', log_files['journal'])


class Journal(AtomicDEVS):
    """
    Journal DEVS Atomic model. It keeps track of the latest updates in orderbooks and market state, and transmits some
    of this information to the agent that interact with the market. This is a service that the journal provides to
    the agent that have a subscription to the journal
    """
    def __init__(self, identifier, input_ports, output_ports):
        AtomicDEVS.__init__(self, identifier)
        self.identifier = identifier
        for port_name in input_ports:
            setattr(self, port_name, self.addInPort(port_name))
        for port_name in output_ports:
            setattr(self, port_name, self.addOutPort(port_name))
        logger.debug("Initialized journal. in_ports = %s | out_ports = %s" % (str(input_ports), str(output_ports)))

    # TODO: add this methods in all atomic devs!
    def get_elapsed(self):
        return self.elapsed

    def get_devs_model(self):
        return self

    def intTransition(self):
        """
        Execute scheduled tasks
        :return:
        """
        logger.debug("====================> Internal Transition (%f)" % self.state.current_time)
        self.state.remaining = self.manager.process_internal_transition()
        if self.state.remaining != float('inf'):
            # Update current_time (for next time it wakes up; only when time advance is < inf)
            self.state.current_time += self.state.remaining
            logger.debug("Update next current_time = %f" % self.state.current_time)
        return self.state

    def timeAdvance(self):
        """
        Determines remaining time left until next internal transition. Always set up as self.state.remaining
        :return: float
        """
        logger.debug("(clock) time advance: %f" % self.state.remaining)
        return self.state.remaining

    def outputFnc(self):
        """
        Output notifications determined by self.state every before executing every scheduled internal transition. The
        state determines which message to send through each output port
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

    @updating_current_time_with_manager
    def extTransition(self, inputs):
        """
        React to external input by scheduling tasks. Explicitly specify all input ports that are available. The manager
        determines how the journal's state has to change, and returns a numeric value for time remaining until wakeup
        :param inputs:
        :return: JournalState
        """
        logger.debug("====================> External transition (%f)" % self.state.current_time)
        map_method = {
            'in_agent': self.manager.process_in_agent,
            'in_orderbook': self.manager.process_in_orderbook
        }
        assert (set(map_method.keys()).issubset(set([port.name for port in self.ports if port.is_input])))
        input_match = list(filter(lambda x: x.name in map_method.keys(), inputs.keys()))
        if len(input_match) != 1:
            raise Exception('Not implemented: implemented only in_agent and in_orderbook')
        else:
            self.state.remaining = map_method[input_match[0].name](inputs[input_match[0]])
        return self.state
