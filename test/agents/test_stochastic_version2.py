import unittest
from pypdevs.simulator import Simulator
from src.exchange.orderbook.orderbook_version1 import OrderbookVersion1
from src.system.simple_system import SimpleSystem
from src.strategies.replay.replay_version3 import ReplayVersion3Strategy
from src.strategies.stochastic.stochastic_version2 import StochasticStrategy2
from src.strategies.stochastic.stochastic_version3 import StochasticStrategy3
from src.strategies.stochastic.stochastic_version4 import StochasticStrategy4
from src.exchange.structures.version2_exchange import Version2Exchange
from src.agent.agent_base import AgentBase
import functools
import pandas as pd
import random
from src.strategies.arbitrage.arbitrage_2 import ArbitrageurVersion1


class MultipleStochasticAgents(unittest.TestCase):

    def simulate(self, current_time, end_time, agents, receiver_agents, agents_delay_map, contracts, delay_order,
                 delay_notification):
        start_time = 0.0
        market_input_ports = ['in_agent_regulator', 'in_agent_journal']
        market_output_ports = ['out_next_journal_agent', 'out_notify_order_journal_agent', 'out_next_regulator_agent']
        orderbooks_map = {
            contract: OrderbookVersion1('ob_' + contract, contract, delay_order, delay_notification)
            for contract in contracts}
        market = Version2Exchange('market', current_time, float('inf'), orderbooks_map.values(),
                                  market_input_ports, market_output_ports, agents_delay_map,
                                  start_time=start_time, end_time=end_time)
        connections = [((agent.identifier, 'out_order'), (market.identifier, 'in_agent_regulator'))
                       for agent in agents]
        # Reactive agent observes the output from journal
        connections += [((market.identifier, 'out_next_journal_agent'), (agent.identifier, 'in_next'))
                        for agent in receiver_agents]
        connections += [((market.identifier, 'out_notify_order_journal_agent'), (agent.identifier, 'in_notify_order'))
                        for agent in receiver_agents]
        connections += [((market.identifier, 'out_next_regulator_agent'), (agent.identifier, 'in_notify_order'))
                        for agent in receiver_agents]
        m = SimpleSystem(market=market, agents=agents, connections=connections)
        sim = Simulator(m)
        sim.setClassicDEVS()
        sim.simulate()
        return sim

    # @unittest.skip("skip")
    def test_stochastic_1(self):
        current_time = 0.0
        end_time = 40
        # Setup contracts for test
        contracts = ['INTC']
        ls = [(0, 0)]
        for delay_order, delay_notification in ls:
            agents, receiver_agents = [], []
            agents_delay_map = {}
            agent_ids = [1, 2]
            wakeup_distribution = functools.partial(random.expovariate, 0.5)
            for agent_id in agent_ids:
                # Initialize parameters
                if agent_id % 2 == 0:
                    price_distribution = lambda: random.normalvariate(14, 3)
                    direction = -1
                else:
                    price_distribution = lambda: random.normalvariate(5, 3)
                    direction = 1
                contract = 'INTC'
                exec_type = 0  # Limit

                # Initialize agent
                identifier = 'stc_' + str(agent_id)
                new_agent = AgentBase(identifier=identifier, strategy=StochasticStrategy2,
                                      strategy_params={'identifier': identifier+'_strategy',
                                                       'wakeup_distribution': wakeup_distribution,
                                                       'direction': direction,
                                                       'price_distribution': price_distribution,
                                                       'contract': contract, 'exec_type': exec_type,
                                                       'end_time': end_time})
                agents.append(new_agent)
                agents_delay_map[new_agent.identifier] = 0
                receiver_agents.append(new_agent)

            # Simulate
            self.simulate(current_time, end_time, agents, receiver_agents, agents_delay_map, contracts,
                          delay_order, delay_notification)


    # @unittest.skip("skip")
    def test_stochastic_with_arbitrage(self):
        current_time = 0.0
        end_time = 40

        # Setup contracts for test
        contracts = ['INTC', 'IBM']
        delay_order, delay_notification = 0, 0

        agents, receiver_agents = [], []
        agents_delay_map = {}
        # Stochastic agents
        agents_info = [
            {'agent_id': 2, 'contract': 'IBM', 'direction': -1,
             'price_distribution': functools.partial(random.normalvariate, 55, 1)},  # spread ~ 30
            {'agent_id': 1, 'contract': 'IBM', 'direction': 1,
             'price_distribution': functools.partial(random.normalvariate, 50, 1)},
            # => spread(bid_IBM, ask_INTC) ~ 10
            {'agent_id': 4, 'contract': 'INTC', 'direction': -1,
             'price_distribution': functools.partial(random.normalvariate, 60, 2)},  # spread ~ 30
            {'agent_id': 3, 'contract': 'INTC', 'direction': 1,
             'price_distribution': functools.partial(random.normalvariate, 55, 2)}

        ]
        wakeup_distribution = functools.partial(random.expovariate, 0.5)
        for agent_info in agents_info:

            # Initialize parameters
            agent_id = agent_info['agent_id']
            direction = agent_info['direction']
            contract = agent_info['contract']
            price_distribution = agent_info['price_distribution']
            # In common
            exec_type = 0  # Limit
            # Initialize agent
            identifier = 'stc_' + str(agent_id)
            new_agent = AgentBase(identifier=identifier, strategy=StochasticStrategy2,
                                  strategy_params={'identifier': identifier,
                                                   'wakeup_distribution': wakeup_distribution,
                                                   'direction': direction,
                                                   'price_distribution': price_distribution,
                                                   'contract': contract, 'exec_type': exec_type,
                                                   'end_time': end_time})
            agents.append(new_agent)
            agents_delay_map[new_agent.identifier] = 0
            # All agents receive all information (a lot of messages)
            receiver_agents.append(new_agent)

        # Arbitragist agent
        arbitragist_id = 'arbitragist'
        arbitragist_agent = AgentBase(identifier=arbitragist_id, strategy=ArbitrageurVersion1,
                                      strategy_params={
                                          'identifier': arbitragist_id,
                                          'end_time': end_time
                                      })
        agents.append(arbitragist_agent)
        agents_delay_map[arbitragist_agent.identifier] = 0.0
        receiver_agents.append(arbitragist_agent)
        # Simulate
        self.simulate(current_time, end_time, agents, receiver_agents, agents_delay_map, contracts,
                      delay_order, delay_notification)

    # @unittest.skip("skip")
    def test_stochastic_with_arbitrage_and_price_dependent_on_time(self):
        current_time = 0.0
        end_time = 40

        # Setup contracts for test
        contracts = ['INTC', 'IBM']
        delay_order, delay_notification = 0, 0

        agents, receiver_agents = [], []
        agents_delay_map = {}
        # Stochastic agents
        agents_info = [
            {'agent_id': 2, 'contract': 'IBM', 'direction': -1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t+25, 1)},  # spread ~ 30
            {'agent_id': 1, 'contract': 'IBM', 'direction': 1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t+20, 1)},
            # => spread(bid_IBM, ask_INTC) ~ 10
            {'agent_id': 4, 'contract': 'INTC', 'direction': -1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t+14, 2)},  # spread ~ 30
            {'agent_id': 3, 'contract': 'INTC', 'direction': 1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t+4, 2)}

        ]
        wakeup_distribution = functools.partial(random.expovariate, 0.5)
        for agent_info in agents_info:
            # Initialize parameters
            agent_id = agent_info['agent_id']
            direction = agent_info['direction']
            contract = agent_info['contract']
            price_distribution = agent_info['price_distribution']
            # In common
            exec_type = 0  # Limit
            # Initialize agent
            identifier = 'stc_' + str(agent_id)
            new_agent = AgentBase(identifier=identifier, strategy=StochasticStrategy3,
                                  strategy_params={'identifier': identifier,
                                                   'wakeup_distribution': wakeup_distribution,
                                                   'direction': direction,
                                                   'price_distribution': price_distribution,
                                                   'contract': contract, 'exec_type': exec_type,
                                                   'end_time': end_time})
            agents.append(new_agent)
            agents_delay_map[new_agent.identifier] = 0
            # All agents receive all information (a lot of messages)
            receiver_agents.append(new_agent)

        # Arbitragist agent
        arbitragist_id = 'arbitragist'
        arbitragist_agent = AgentBase(identifier=arbitragist_id, strategy=ArbitrageurVersion1,
                                      strategy_params={
                                          'identifier': arbitragist_id,
                                          'end_time': end_time
                                      })
        agents.append(arbitragist_agent)
        agents_delay_map[arbitragist_agent.identifier] = 0.0
        receiver_agents.append(arbitragist_agent)
        # Simulate
        self.simulate(current_time, end_time, agents, receiver_agents, agents_delay_map, contracts,
                      delay_order, delay_notification)

    # @unittest.skip("skip")
    def test_impact_at_t10(self):
        current_time = 0.0
        end_time = 40

        # Setup contracts for test
        contracts = ['INTC', 'IBM']
        delay_order, delay_notification = 0, 0

        agents, receiver_agents = [], []
        agents_delay_map = {}
        # Stochastic agents
        agents_info = [
            {'agent_id': 2, 'contract': 'IBM', 'direction': -1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t + 25, 1)},  # spread ~ 30
            {'agent_id': 1, 'contract': 'IBM', 'direction': 1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t + 20, 1)},
            # => spread(bid_IBM, ask_INTC) ~ 10
            {'agent_id': 4, 'contract': 'INTC', 'direction': -1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t + 14, 2)},  # spread ~ 30
            {'agent_id': 3, 'contract': 'INTC', 'direction': 1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t + 4, 2)}

        ]
        wakeup_distribution = functools.partial(random.expovariate, 0.5)
        for agent_info in agents_info:
            # Initialize parameters
            agent_id = agent_info['agent_id']
            direction = agent_info['direction']
            contract = agent_info['contract']
            price_distribution = agent_info['price_distribution']
            # In common
            exec_type = 0  # Limit
            # Initialize agent
            identifier = 'stc_' + str(agent_id)
            new_agent = AgentBase(identifier=identifier, strategy=StochasticStrategy3,
                                  strategy_params={'identifier': identifier,
                                                   'wakeup_distribution': wakeup_distribution,
                                                   'direction': direction,
                                                   'price_distribution': price_distribution,
                                                   'contract': contract, 'exec_type': exec_type,
                                                   'end_time': end_time})
            agents.append(new_agent)
            agents_delay_map[new_agent.identifier] = 0
            # All agents receive all information (a lot of messages)
            receiver_agents.append(new_agent)

        # Arbitragist agent
        impact_agent_id = 'impact'
        history = pd.read_csv('agents_data/impact_3.csv')
        impact_agent = AgentBase(identifier=impact_agent_id, strategy=ReplayVersion3Strategy,
                                 strategy_params={
                                      'identifier': impact_agent_id, 'history': history
                                 })
        agents.append(impact_agent)
        agents_delay_map[impact_agent.identifier] = 0.0
        receiver_agents.append(impact_agent)
        # Simulate
        self.simulate(current_time, end_time, agents, receiver_agents, agents_delay_map, contracts,
                      delay_order, delay_notification)

    # @unittest.skip("skip")
    def test_impact_with_cancellation(self):
        current_time = 0.0
        end_time = 20


        # Setup contracts for test
        contracts = ['INTC', 'IBM']
        delay_order, delay_notification = 0, 0

        agents, receiver_agents = [], []
        agents_delay_map = {}
        # Stochastic agents
        agents_info = [
            {'agent_id': 2, 'contract': 'IBM', 'direction': -1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t + 25, 1)},  # spread ~ 30
            {'agent_id': 1, 'contract': 'IBM', 'direction': 1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t + 20, 1)},
            # => spread(bid_IBM, ask_INTC) ~ 10
            {'agent_id': 4, 'contract': 'INTC', 'direction': -1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t + 14, 2)},  # spread ~ 30
            {'agent_id': 3, 'contract': 'INTC', 'direction': 1,
             'price_distribution': lambda t: functools.partial(random.normalvariate, t + 4, 2)}

        ]
        wakeup_distribution = functools.partial(random.expovariate, 0.5)
        for agent_info in agents_info:
            # Initialize parameters
            agent_id = agent_info['agent_id']
            direction = agent_info['direction']
            contract = agent_info['contract']
            price_distribution = agent_info['price_distribution']
            # In common
            exec_type = 0  # Limit
            # Initialize agent
            identifier = 'stc_' + str(agent_id)
            new_agent = AgentBase(identifier=identifier, strategy=StochasticStrategy4,
                                  strategy_params={'identifier': identifier,
                                                   'wakeup_distribution': wakeup_distribution,
                                                   'cancellation_timeout': 2,
                                                   'direction': direction,
                                                   'price_distribution': price_distribution,
                                                   'contract': contract, 'exec_type': exec_type,
                                                   'end_time': end_time})
            agents.append(new_agent)
            agents_delay_map[new_agent.identifier] = 0
            # All agents receive all information (a lot of messages)
            receiver_agents.append(new_agent)

        # Arbitragist agent
        impact_agent_id = 'impact'
        history = pd.read_csv('agents_data/impact_3.csv')
        impact_agent = AgentBase(identifier=impact_agent_id, strategy=ReplayVersion3Strategy,
                                 strategy_params={
                                      'identifier': impact_agent_id, 'history': history
                                 })
        agents.append(impact_agent)
        agents_delay_map[impact_agent.identifier] = 0.0
        receiver_agents.append(impact_agent)
        # Simulate
        self.simulate(current_time, end_time, agents, receiver_agents, agents_delay_map, contracts,
                      delay_order, delay_notification)

if __name__ == '__main__':
    unittest.main()
