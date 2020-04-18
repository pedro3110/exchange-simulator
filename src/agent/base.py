from pypdevs.DEVS import AtomicDEVS
from src.utils.debug import Debug


class AgentBase(AtomicDEVS, Debug):
    """
    Agent that interacts with the market only by sending a deterministic set of orders to execute
    """
    def __init__(self, identifier, strategy, strategy_params):
        AtomicDEVS.__init__(self, identifier)
        self.identifier = identifier

        # I/O Ports
        self.in_notify_order = self.addInPort("in_notify_order")
        self.in_next = self.addInPort("in_next")

        self.last_transition = None  # [internal, external]
        self.last_elapsed = 0.0

        self.out_order = self.addOutPort("out_order")
        self.output_ports = {'out_order'}

        self.last_current_time = 0.0

        self.strategy = strategy(self, **strategy_params)
        self.time_advance = self.strategy.next_wakeup_time
        self.last_time_advance = None

    def get_identifier(self):
        return self.identifier

    def get_elapsed(self):
        assert (self.elapsed is not None)
        return self.elapsed

    def get_current_time(self):
        return self.last_current_time

    def timeAdvance(self):
        self.debug("(clock) time advance: %f" % self.get_time_advance())
        return self.get_time_advance()

    def get_time_advance(self):
        if self.time_advance < -0.001:
            raise Exception('Negative time advance: %f' % self.time_advance)
        else:
            self.time_advance = max(0, self.time_advance)
        return self.time_advance

    def outputFnc(self):
        elapsed = self.get_time_advance()
        self.debug("last_elapsed=%f elapsed=%f" % (self.last_elapsed, elapsed))
        self.debug("====================> Output function (%f, %f, %f)" % (
            self.get_current_time(), self.get_time_advance(), self.get_current_time() + elapsed))

        output = self.strategy.output_function(self.last_current_time, elapsed)
        output_mapped = {getattr(self, k): v for k, v in output.items()}
        return output_mapped

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

        map_method = {'in_notify_order': self.strategy.process_in_notify_order,
                      'in_next': self.strategy.process_in_next}
        assert (set(map_method.keys()).issubset(set([port.name for port in self.ports if port.is_input])))
        input_match = list(filter(lambda x: x.name in map_method.keys(), inputs.keys()))
        ta = float('inf')
        for match in input_match:
            message = inputs[match]
            ta = min(ta, map_method[match.name](self.get_current_time(), elapsed, message))
        # Updates
        self.last_elapsed = ta
        self.time_advance = ta
        self.last_current_time += elapsed
        self.debug("(extTransition) Update time_advance = %f" % self.time_advance)
        return self.strategy
