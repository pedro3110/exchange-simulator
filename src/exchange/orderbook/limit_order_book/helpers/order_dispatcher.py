from src.exchange.orders.order_utils import OrderStatus, Direction
from src.exchange.orderbook.limit_order_book.helpers.lob_notification import LOBTableNotification
from src.utils.debug import Debug


class OrderDispatcher(Debug):
    """
    Dispatch order to processing engine and return notification of results
    Methods
    -------
    dispatch_order : Order
        dispatch order
    _update : Order
        does some preprocessing and if not rejected, it sends the order to the processing engine
    """
    def __init__(self, table, queue_operator, order_processor):
        super(OrderDispatcher, self).__init__()
        self.table = table
        self.queue_operator = queue_operator
        self.order_processor = order_processor

    def get_identifier(self):
        return "order_dispatcher"

    def dispatch_order(self, order):
        """
        Dispatch Sell/Buy/Cancel orders
        :param order: Order
        :return: LOBTableNotification
        """
        if order.direction == Direction.Sell:
            self.debug('Dispatch order: %i (Sell)' % order.m_orderId)
            return self._update(order)
        elif order.direction == Direction.Cancel:
            self.debug('Dispatch order: %i (Cancel)' % order.m_orderId)
            return self.order_processor.cancel(order)
        elif order.direction == Direction.Buy:
            self.debug('Dispatch order: %i (Buy)' % order.m_orderId)
            return self._update(order)
        else:
            raise Exception('Error is_buy_order = %i not implemented' % order.m_orderId)

    def _update(self, last_order):
        """
        Enqueue a Buy/Sell order. Check for matched orders, following the Rules (c, d, e, f, g, h):
            1. Active buy (Partial/Accepted)  + sell with px_sell <= px_buy
            2. Active sell (Partial/Accepted) + buy with px_sell <= px_buy
        :return: LOBTableNotification
        """
        last_order = self.table.order_checker.checked_classified(last_order)
        if last_order.get_status() is OrderStatus.Rejected:
            self.debug("Order %i Rejected" % last_order.m_orderId)
            return LOBTableNotification(rejected=[last_order])
        elif last_order.get_status() is OrderStatus.Accepted:
            self.debug('Order %i Accepted' % last_order.m_orderId)
            self.queue_operator.push(last_order)
            if self.queue_operator.bid_empty() or self.queue_operator.ask_empty():
                self.debug("Match BID/ASK: Fail. Order Accepted")
                return self.order_processor.process_accepted(last_order)
            else:
                self.debug("Match BID/ASK: Matching algorithm")
                return self.order_processor.process_matching(last_order)
        else:
            raise Exception('Order used to update must have status in [Accepted, Rejected]')
