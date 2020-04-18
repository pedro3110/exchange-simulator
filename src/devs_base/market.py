from pypdevs.DEVS import CoupledDEVS
from src.utils.debug import Debug


class MarketState:
    def __init__(self, devs_model, tick_size=1/16., start_time=0.0, end_time=float('inf')):
        self.devs_model = devs_model
        self.tick_size = tick_size
        self.start_time = start_time

        self.current_time = 0.0
        self.end_time = end_time
        self.remaining = float('inf')
        assert(self. start_time < self.end_time)

    def get_devs_model(self):
        return self.devs_model


class Market(CoupledDEVS, Debug):
    """
    A Market is a system of objects which can act as a means of support to the interaction of a big number of agent
    in an asynchronous way
    ======================> for now, it only forwards messages. In the future it will also be able to answer to
    a number of different requests, for example asking for information about the state of the market
    DEVS Components
    ---------------
    journal : Journal
        handles subscriptions from agent and provides information about the status of the market & orderbooks
    regulator : Regulator
        is in charge of regulating the market interactions (ie.: enforcement of certain rules)
    orderbooks : Dict{str : Orderbook}
        a dictionary which keeps an Orderbook (Atomic DEVS) for each contract (str)
    """
    def __init__(self, identifier, market_orderbooks, input_ports, output_ports,
                 internal_connections, external_input_connections, external_output_connections,
                 regulator=None, journal=None):
        CoupledDEVS.__init__(self, identifier)
        self.identifier = identifier
        self.state = MarketState(devs_model=self)

        orderbooks = {orderbook.identifier: self.addSubModel(orderbook) for orderbook in market_orderbooks}
        regulator = self.addSubModel(regulator)
        journal = self.addSubModel(journal)

        # Make it accessible outside of our own scope
        self.journal = journal
        self.regulator = regulator
        self.orderbooks = orderbooks

        all_components = {
            component.identifier: component
            for component in [regulator, journal] + list(orderbooks.values())
        }

        # IOPorts initialization
        for port_name in input_ports:
            setattr(self, port_name, self.addInPort(port_name))
        for port_name in output_ports:
            setattr(self, port_name, self.addOutPort(port_name))

        # External input connections
        for left, right in external_input_connections:
            component_port_from = getattr(self, left)
            component_port_to = getattr(all_components[right[0]], right[1])
            self.connectPorts(component_port_from, component_port_to)
        # External output connections
        for left, right in external_output_connections:
            component_port_from = getattr(all_components[left[0]], left[1])
            component_port_to = getattr(self, right)
            self.connectPorts(component_port_from, component_port_to)
        # Internal connections
        for left, right in internal_connections:
            component_port_from = getattr(all_components[left[0]], left[1])
            component_port_to = getattr(all_components[right[0]], right[1])
            self.connectPorts(component_port_from, component_port_to)

    def get_identifier(self):
        return "market"

    def intTransition(self):
        """
        Only make an internal transition when:
            - t=0 (init simulation)
            - the market is affected by an external input
            - (TODO) some internal process finished execution and action should be taken
        :return: MarketState
        """
        self.debug("====================> Internal transition" % self.state.current_time)
        self.state.remaining = float('inf')
        return self.state

    def timeAdvance(self):
        """
        Always determined by the market's state
        :return: float
        """
        return self.state.remaining

    def outputFnc(self):
        """
        React to transmit information from the internal components of the market to the external agents
        :return:
        """
        self.debug("====================> Output function" % self.state.current_time)
        return {}

    def extTransition(self, inputs):
        """
        Handles input by agent that want to interact with the market
        :param inputs: Dictionary of messages
        :return: MarketState
        """
        self.debug("====================> External transition" % self.state.current_time)
        return self.state
