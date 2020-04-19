from pypdevs.DEVS import CoupledDEVS
from src.utils.debug import Debug


class Exchange(CoupledDEVS, Debug):
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
        raise NotImplemented()
