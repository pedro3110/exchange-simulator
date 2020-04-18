from pypdevs.DEVS import AtomicDEVS
from src.utils.decorators.external_transition import updating_current_time_with_state
from src.utils.decorators.external_transition import market_model_updating_market_current_time
from src.utils.config import get_logger, log_files
logger = get_logger('regulator', log_files['regulator'])


class Regulator(AtomicDEVS):
    """
    A basic Market Regulator.
    Every market must have a regulator to make sure the interactions between agent follow certain rules
    The regulator can directly reject/accept orders or, alternatively, relay on someone else (for example, in an OB)
    """
    def __init__(self, identifier, input_ports, output_ports):
        AtomicDEVS.__init__(self, identifier)
        self.identifier = identifier
        for port_name in input_ports:
            setattr(self, port_name, self.addInPort(port_name))
        for port_name in output_ports:
            setattr(self, port_name, self.addOutPort(port_name))
        logger.debug("Initialized regulator. in_ports = %s | out_ports = %s" % (str(input_ports), str(output_ports)))

    def intTransition(self):
        logger.debug("====================> Internal Transition (%f)" % self.state.current_time)
        self.state.remaining = self.state.process_internal_transition()
        if self.state.remaining != float('inf'):
            # Update current_time (for next time it wakes up; only when time advance is < inf)
            self.state.current_time += self.state.remaining
            logger.debug("Update next current_time = %f" % self.state.current_time)
        return self.state

    def timeAdvance(self):
        logger.debug("(clock) time advance: %f" % self.state.remaining)
        return self.state.remaining

    def outputFnc(self):
        logger.debug("====================> Output function (%f)" % self.state.current_time)
        output_ports = {port.name for port in self.ports if not port.is_input}
        map_portname_output = self.state.outputFnc(output_ports)
        output_messages = {
            next(iter(filter(lambda x: x.name is portname, self.ports)), None): message
            for portname, message in map_portname_output.items()
        }
        return output_messages

    def get_elapsed(self):
        return self.elapsed

    @updating_current_time_with_state
    @market_model_updating_market_current_time
    def extTransition(self, inputs):
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

