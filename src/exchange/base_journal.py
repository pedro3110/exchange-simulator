from pypdevs.DEVS import AtomicDEVS
from src.utils.debug import Debug


class JournalBase(AtomicDEVS, Debug):
    def __init__(self, identifier, strategy, strategy_params):
        AtomicDEVS.__init__(self, identifier)
        self.identifier = identifier
        self.strategy = strategy(self, **strategy_params)

        self.last_elapsed = 0.0
        self.last_current_time = 0.0

        self.time_advance = self.strategy.next_wakeup_time
        self.last_time_advance = None

        # I/O Ports
        self.in_notify_order = self.addInPort("in_orderbook")
        self.in_next = self.addInPort("in_next")

        self.out_next = self.addOutPort("out_next")
        self.out_notify_order = self.addOutPort("out_notify_order")
        self.output_ports = {'out_next', 'out_notify_order'}

    def get_identifier(self):
        return self.identifier

    def get_elapsed(self):
        assert (self.elapsed is not None)
        return self.elapsed

    def get_current_time(self):
        return self.last_current_time

    def timeAdvance(self):
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
        output = self.strategy.output_function(self.last_current_time, elapsed)
        output_mapped = {getattr(self, k): v for k, v in output.items()}
        return output_mapped

    def intTransition(self):
        elapsed = self.get_time_advance()
        ta = self.strategy.process_internal(self.get_current_time(), elapsed)
        self.time_advance = ta
        self.last_elapsed = ta
        self.last_current_time += elapsed
        return self.state

    def extTransition(self, inputs):
        elapsed = self.get_elapsed()
        map_method = {
            'in_orderbook': self.strategy.process_in_orderbook,
            'in_next': self.strategy.process_in_next
        }
        assert (set(map_method.keys()).issubset(set([port.name for port in self.ports if port.is_input])))
        input_match = list(filter(lambda x: x.name in map_method.keys(), inputs.keys()))
        ta = float('inf')
        for match in input_match:
            message = inputs[match]
            ta = min(ta, map_method[match.name](self.get_current_time(), elapsed, message))
        self.last_elapsed = ta
        self.time_advance = ta
        self.last_current_time += elapsed
        return self.strategy
