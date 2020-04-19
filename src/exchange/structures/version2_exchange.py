from src.exchange.base_exchange import Exchange
from src.exchange.journal.journal_version1 import JournalVersion1
from src.exchange.regulator.regulator_version1 import BasicRegulatorVersion1


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


class Version2Exchange(Exchange):
    """
    Contains the components and internal connections of the possibly most basic composition of a market
    """
    def __init__(self,
                 identifier, current_time, remaining, market_orderbooks, input_ports, output_ports, agents_delay_map,
                 tick_size=0.001, start_time=0.0, end_time=float('inf')):

        # Initialize tick size of each orderbook
        self.identifier = identifier
        self.start_time = start_time
        self.end_time = end_time
        self.tick_size = tick_size
        for ob in market_orderbooks:
            ob.set_tick_size(tick_size)

        # Initialize timing and status
        assert(current_time >= self.start_time)
        assert(current_time < self.end_time)
        self.active = True

        # Initialize components of this specific market
        # => Regulator (input ports)
        regulator_input_ports = ['in_order']
        # => Regulator (output ports). Each output port has an identifier => output port name
        regulator_contract_port_map = {ob.contract: 'out_'+ob.contract for ob in market_orderbooks}
        regulator_contract_port_map['out_order'] = 'out_order'

        # => Connect out_order of Regulator with out_journal_agent
        regulator = BasicRegulatorVersion1(self, 'regulator', regulator_input_ports,
                                           regulator_contract_port_map, agents_delay_map)
        # => Journal
        journal_identifier = 'journal_1'
        journal = JournalVersion1(self, journal_identifier)

        # Regulator => orderbooks
        internal_connections = [
            ((regulator.identifier, 'out_' + orderbook.contract), (orderbook.identifier, 'in_order'))
            for orderbook in market_orderbooks
            ]
        # orderbooks => journal
        internal_connections += [
            ((orderbook.identifier, 'out_journal'), (journal.identifier, 'in_orderbook'))
            for orderbook in market_orderbooks
        ]

        # External input connections (port_from, (component_to, port_to))
        external_input_connections = [
            ('in_agent_journal', (journal.identifier, 'in_agent')),          # agent => journal (subscriptions)
            ('in_agent_regulator', (regulator.identifier, 'in_order'))       # agent => regulator (orders)
        ]
        # External output connections ((component_from, port_from), port_to)
        external_output_connections = [
            ((journal.identifier, 'out_next'), 'out_next_journal_agent'),
            ((journal.identifier, 'out_notify_order'), 'out_notify_order_journal_agent'),

            # Only to notify cancelations (TODO)
            ((regulator.identifier, 'out_order'), 'out_next_regulator_agent')  # regulator => agent
        ]

        # Initialize market with desired components
        super(Version2Exchange, self).__init__(identifier, market_orderbooks,
                                               input_ports, output_ports, internal_connections,
                                               external_input_connections, external_output_connections,
                                               regulator, journal)
        self.state = MarketState(self, tick_size, start_time, end_time)

    def get_identifier(self):
        return self.identifier
