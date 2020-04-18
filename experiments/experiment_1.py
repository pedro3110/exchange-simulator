import sys

root_path = '/home/pedro/Desktop/agent-based-models/PythonPDEVS/src/'
example_path = '/home/pedro/Desktop/agent-based-models/PythonPDEVS/examples/cda/'
sys.path.append(root_path)
sys.path.append(example_path)

from pypdevs.DEVS import CoupledDEVS
from system_base.market import Market
from agent.deprecated.simple_agent_to_journal import SimpleAgentToJournal

from utils.config import get_logger, log_files
logger = get_logger('system', log_files['system'])


class Experiment1(CoupledDEVS):
    def __init__(self):
        CoupledDEVS.__init__(self, "System")

        # Parametrization of a simple market
        contracts = ['IBM']
        # TODO: check that every contract has a unique string identifier
        # each contract will have exactly one corresponding order book. TODO: parametrize the creation of each OB
        market = self.addSubModel(Market(contracts))

        # TODO: parametrize the creation of each Agent (simple vs. with intermediary vs. more complex, etc.)
        agents = [
            self.addSubModel(SimpleAgentToJournal())
        ]

        # Subscribe agent to market journal
        for agent in agents:
            self.connectPorts(agent.out_journal, market.in_agent_journal)

        # There are two types of agent:
        #  those that receive EVERY message from the market and can decide what to do with it and
        #  those that receive ONLY messages sent to him
        for agent in agents:
            if isinstance(agent, SimpleAgentToJournal):
                self.connectPorts(market.out_journal_agent, agent.in_next_orderbook)
                self.connectPorts(market.out_regulator_agent, agent.in_notify_order)
            else:
                # TODO: create specific port for this agent in the market coupled class
                pass


# Experiment
from pypdevs.simulator import Simulator
m = Experiment1()
sim = Simulator(m)
sim.setClassicDEVS()
sim.simulate()
