import sys
root_path = '/home/pedro/Desktop/agent-based-models/PythonPDEVS/src/'
example_path = '/home/pedro/Desktop/agent-based-models/PythonPDEVS/examples/cda/'
sys.path.append(root_path)
sys.path.append(example_path)

from pypdevs.DEVS import CoupledDEVS


class SimpleSystem(CoupledDEVS):
    """
    Most basic system of agents <=> market
    """
    def __init__(self, market, agents, connections):
        CoupledDEVS.__init__(self, "AgentMarketSystem")
        market = self.addSubModel(market)
        agents = [self.addSubModel(agent) for agent in agents]
        all_components = {
            component.identifier: component for component in [market] + agents
        }
        # Internal connections
        for left, right in connections:
            component_port_from = getattr(all_components[left[0]], left[1])
            component_port_to = getattr(all_components[right[0]], right[1])
            self.connectPorts(component_port_from, component_port_to)

        # Make available outside
        self.market = market
        self.agents = {
            agent.identifier: agent
            for agent in agents
        }
