from src.exchange.orders.order_utils import Direction, Exectype
from src.exchange.orderbook.limit_order_book.helpers.queue_observer import QueueObserver
from src.utils.debug import Debug
import heapq


class QueueOperator(QueueObserver, Debug):
    def __init__(self, table):
        super(QueueOperator, self).__init__(table)

    def get_identifier(self):
        return "queue_operator"

    def pop_bid(self):
        if not self.market_bid_empty():
            return self.table.order_checker.checked_expired(heapq.heappop(self.table.market_bid))
        else:
            return self.table.order_checker.checked_expired(heapq.heappop(self.table.bid))

    def pop_ask(self):
        if not self.market_ask_empty():
            return self.table.order_checker.checked_expired(heapq.heappop(self.table.market_ask))
        else:
            return self.table.order_checker.checked_expired(heapq.heappop(self.table.ask))

    def pop_bid_by_id(self, order_id):
        """
        Method for getting inside the priority queue (bid table) and remove the order with id = order_id
        If there is no matching order, it returns None. Must check in al queues (Limit & Market orders).
        When poping, must also check if the order has expired!
        :param order_id:
        :return: Order or None
        """
        self.debug("Popping BUY order: %i" % order_id)

        # Assumes that priority queue doesn't have repeated id's
        index_limit = [i for i, order in enumerate(self.table.bid) if order.m_orderId == order_id]
        index_market = [i for i, order in enumerate(self.table.market_bid) if order.m_orderId == order_id]
        assert(len(index_limit) <= 1)
        if len(index_limit) > 0:
            matched_bid = self.table.bid[index_limit[0]]
            self.table.bid[index_limit[0]] = self.table.bid[-1]
            self.table.bid.pop()
            heapq.heapify(self.table.bid)
            return True, self.table.order_checker.checked_expired(matched_bid)
        elif len(index_market) > 0:
            matched_bid = self.table.market_bid[index_market[0]]
            self.table.market_bid[index_market[0]] = self.table.market_bid[-1]
            self.table.market_bid.pop()
            heapq.heapify(self.table.market_bid)
            return True, self.table.order_checker.checked_expired(matched_bid)
        else:
            return False, None

    def pop_ask_by_id(self, order_id):
        """
        Method for getting inside the priority queue (ask table) and remove the order with id = order_id
        If there is no matching order, it returns None. Must check in al queues (Limit & Market orders).
        When poping, must also check if the order has expired!
        :param order_id:
        :return: Order or None
        """
        self.debug("Popping SELL order: %i" % order_id)

        # Assumes that priority queue doesn't have repeated id's
        index_limit = [i for i, order in enumerate(self.table.ask) if order.m_orderId == order_id]
        index_market = [i for i, order in enumerate(self.table.market_ask) if order.m_orderId == order_id]
        assert(len(index_limit) <= 1)
        if len(index_limit) > 0:
            matched_ask = self.table.ask[index_limit[0]]
            self.table.ask[index_limit[0]] = self.table.ask[-1]
            self.table.ask.pop()
            heapq.heapify(self.table.ask)
            return True, self.table.order_checker.checked_expired(matched_ask)
        elif len(index_market) > 0:
            matched_ask = self.table.market_ask[index_market[0]]
            self.table.market_ask[index_market[0]] = self.table.market_ask[-1]
            self.table.market_ask.pop()
            heapq.heapify(self.table.market_ask)
            return True, self.table.order_checker.checked_expired(matched_ask)
        else:
            return False, None

    def push(self, order):
        # Push to expiration times queue
        heapq.heappush(self.table.expiration_times, (order.expiration_time, order.m_orderId))
        # Push to corresponding queue
        if order.get_exec_type() is Exectype.Limit:
            self.debug('Push Limit Order %i' % order.m_orderId)
            if order.direction is Direction.Buy:
                heapq.heappush(self.table.bid, order)
            elif order.direction is Direction.Sell:
                heapq.heappush(self.table.ask, order)
            else:
                raise Exception('Can only enqueue Buy or Sell orders')
        elif order.get_exec_type() is Exectype.Market:
            self.debug('Push Market Order %i' % order.m_orderId)
            if order.direction is Direction.Buy:
                heapq.heappush(self.table.market_bid, order)
            elif order.direction is Direction.Sell:
                heapq.heappush(self.table.market_ask, order)
            else:
                raise Exception('Can only enqueue Buy or Sell orders')
        else:
            assert(order.get_exec_type() in [Exectype.Stop, Exectype.StopLimit])
            self.debug("Push Stop Order %i" % order.m_orderId)
            self.table.stop.append(order)
        return 0
