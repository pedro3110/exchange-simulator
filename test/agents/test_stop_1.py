import unittest
from pypdevs.simulator import Simulator
from src.exchange.orderbook.orderbook_version1 import OrderbookVersion1
from src.system.simple_system import SimpleSystem
from src.strategies.replay.replay_version3 import ReplayVersion3Strategy
from src.strategies.stochastic.stochastic_version5 import StochasticStrategy5
from src.agent.base import AgentBase
from src.exchange.structures.version2_market import Version2Market
import functools
import pandas as pd
import random


class MultipleStochasticAgents(unittest.TestCase):

    def simulate(self, current_time, end_time, agents, receiver_agents, agents_delay_map, contracts, delay_order,
                 delay_notification):
        start_time = 0.0
        market_input_ports = ['in_agent_regulator', 'in_agent_journal']
        market_output_ports = ['out_next_journal_agent', 'out_notify_order_journal_agent', 'out_next_regulator_agent']
        orderbooks_map = {
            contract: OrderbookVersion1('ob_' + contract, contract, delay_order, delay_notification)
            for contract in contracts}
        market = Version2Market('market', current_time, float('inf'), orderbooks_map.values(),
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
    def test_stop_1(self):
        current_time = 0.0
        start_time = 0.0
        end_time = 30

        # Setup contracts for test
        contracts = ['INTC', 'INTC']
        delay_order, delay_notification = 0, 0

        agents, receiver_agents = [], []
        agents_delay_map = {}

        ########
        # AGENTS
        wakeup_distribution = functools.partial(random.expovariate, 0.5)
        n_sellers = 5
        n_buyers = 5
        # Params price and size
        params_buyers_price = [(0, 2), (3, 5), (5, 2)]
        params_sellers_price = [(16, 3), (18, 2), (20, 1)]

        params_buyers_size = [(5, 2), (5, 2), (5, 2)]
        params_sellers_size = [(10, 2), (10, 2), (10, 2)]

        def get_func_price(delta, sigma):
            def func(t):
                #         base_price = 10 + 10*math.sin(t)
                base_price = 10
                x = functools.partial(random.normalvariate, base_price + delta, sigma)
                return lambda: x()

            return func

        def get_func_size(mu, sigma):
            def func(t):
                x = functools.partial(random.normalvariate, mu, sigma)
                return lambda: int(x())

            return func

        agents_info = []
        i = 1
        for n_seller in range(n_sellers):
            pp = params_sellers_price[n_seller % len(params_sellers_price)]
            ps = params_sellers_size[n_seller % len(params_sellers_size)]
            agents_info.append(
                {'agent_id': i, 'contract': 'INTC', 'direction': -1,
                 'price_distribution': get_func_price(pp[0], pp[1]),
                 'size_distribution': get_func_size(ps[0], ps[1])})
            i += 1

        # Buyers
        for n_buyer in range(n_buyers):
            pp = params_buyers_price[n_buyer % len(params_buyers_price)]
            ps = params_buyers_size[n_buyer % len(params_buyers_size)]
            agents_info.append(
                {'agent_id': i, 'contract': 'INTC', 'direction': 1,
                 'price_distribution': get_func_price(pp[0], pp[1]),
                 'size_distribution': get_func_size(ps[0], ps[1])}
            )
            i += 1

        # Replay Agent
        impact_agent_id = 'impact'
        history = pd.read_csv('agents_data/stop_1.csv')
        impact_agent = AgentBase(identifier=impact_agent_id, strategy=ReplayVersion3Strategy,
                                 strategy_params={
                                     'identifier': impact_agent_id, 'history': history
                                 })
        agents.append(impact_agent)
        agents_delay_map[impact_agent.identifier] = 0.0
        receiver_agents.append(impact_agent)

        # Random agents
        for agent_info in agents_info:
            # Initialize parameters
            agent_id = agent_info['agent_id']
            direction = agent_info['direction']
            contract = agent_info['contract']
            price_distribution = agent_info['price_distribution']
            size_distribution = agent_info['size_distribution']
            # In common
            exec_type = 0  # Limit
            cancellation_timeout = 1000

            # Initialize agent
            identifier = 'stc_' + str(agent_id)
            new_agent = AgentBase(identifier=identifier, strategy=StochasticStrategy5,
                                  strategy_params={'identifier': identifier,
                                                   'wakeup_distribution': wakeup_distribution,
                                                   'cancellation_timeout': cancellation_timeout,
                                                   'direction': direction,
                                                   'price_distribution': price_distribution,
                                                   'size_distribution': size_distribution,
                                                   'contract': contract, 'exec_type': exec_type,
                                                   'end_time': end_time})
            agents.append(new_agent)
            agents_delay_map[new_agent.identifier] = 0
            # All agents receive all information (a lot of messages)
            receiver_agents.append(new_agent)

        # Simulate
        self.simulate(current_time, end_time, agents, receiver_agents, agents_delay_map, contracts,
                      delay_order, delay_notification)

if __name__ == '__main__':
    unittest.main()
