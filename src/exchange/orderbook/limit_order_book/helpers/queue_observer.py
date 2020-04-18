from src.utils.debug import Debug
import heapq


class QueueObserver(Debug):
    """
    Simple methods to inspect the status of queues int Bid Ask Table
    """
    def __init__(self, table):
        super(QueueObserver, self).__init__()
        self.table = table

    def get_spread(self):
        if self.bid_empty() or self.ask_empty():
            return None
        else:
            best_bid = self.best_bid()
            best_ask = self.best_ask()
            return best_ask.price - best_bid.price

    def get_identifier(self):
        return "queue_observer"

    def market_bid_empty(self):
        return len(self.table.market_bid) == 0

    def market_ask_empty(self):
        return len(self.table.market_ask) == 0

    def bid_empty(self):
        return len(self.table.bid) + len(self.table.market_bid) == 0

    def market_bid_size(self):
        return len(self.table.market_bid)

    def market_ask_size(self):
        return len(self.table.market_ask)

    def bid_size(self):
        return len(self.table.bid) + len(self.table.market_bid)

    def ask_empty(self):
        return len(self.table.ask) + len(self.table.market_ask) == 0

    def ask_size(self):
        return len(self.table.ask) + len(self.table.market_ask)

    def get_order_ids(self):
        return self.get_ask_ids() + self.get_bid_ids()

    def get_ask_ids(self):
        return list(map(lambda x: x.m_orderId, self.table.ask))

    def get_bid_ids(self):
        return list(map(lambda x: x.m_orderId, self.table.bid))

    def best_bid(self):
        """
        Get smallest element of the bid queue (most important element in the queue).
        If the market queue contains at least one order, give it priority
        :return:
        """
        if self.bid_empty():
            return None
        else:
            if not self.market_bid_empty():
                # Match the market bids before the regular Exectype of bids
                return self.table.order_checker.checked_expired(heapq.nsmallest(1, self.table.market_bid)[0])
            else:
                # Understanding nsmallest as the 'best' n bid offers
                return self.table.order_checker.checked_expired(heapq.nsmallest(1, self.table.bid)[0])

    def best_ask(self):
        """
        Get smallest element of the ask queue (most important element in the queue).
        If the market queue contains at least one order, give it priority
        :return:
        """
        if self.ask_empty():
            return None
        else:
            if not self.market_ask_empty():
                # Match the market asks beore the regular Exectype of asks
                return self.table.order_checker.checked_expired(heapq.nsmallest(1, self.table.market_ask)[0])
            else:
                # Understanding nsmallest as the 'best' n ask offers
                return self.table.order_checker.checked_expired(heapq.nsmallest(1, self.table.ask)[0])
