from src.exchange.orderbook.limit_order_book.helpers.lob_notification import LOBTableNotification
from src.exchange.orders.order_utils import OrderStatus, Exectype
from src.utils.debug import Debug


class OrderProcessor(Debug):
    """
    Process orders: Match or Cancel
    Methods
    -------
    _execute : a match was found. Execute the transaction
    process_stop_queue:
    process_accepted:
    process_matching:
    """
    def __init__(self, table, transaction_calculator, queue_operator):
        super(OrderProcessor, self).__init__()
        self.table = table
        self.transaction_calculator = transaction_calculator
        self.queue_operator = queue_operator

    def get_identifier(self):
        return "order_processor"

    def match(self):
        """
        Update the status of bid and ask, depending if they can match each other or not.
        It returns a bool (indicating if at least one of the orders was only partially executed) and a tuple,
        with the orders bid and ask, with their status updated accordingly
        :return: Tuple[bool, List[Order]]
        """
        bid = self.queue_operator.pop_bid()  # get smallest order in heap (smallest == with higher priority)
        ask = self.queue_operator.pop_ask()  # get smallest order in heap (smallest == with higher priority)
        both_market_orders = bid.get_exec_type() is Exectype.Market and ask.get_exec_type() is Exectype.Market
        both_limit_orders = bid.get_exec_type() is Exectype.Limit and ask.get_exec_type() is Exectype.Limit
        # No match if bid < ask
        if both_limit_orders and bid.price < ask.price:
            self.debug('Match: False (spread > 0). The orders re re-enqueued')
            self.queue_operator.push(bid)
            self.queue_operator.push(ask)
            return False, [bid, ask]
        # Two possibilities: LvsL / MvsL / LvsM / Market vs. Market
        if not both_market_orders:
            # At least one Limit order.Execute operation with a price (dependent on bid and ask status and exec_type)
            price_executed = self.transaction_calculator.get_price_executed(bid, ask)
            self.debug("Price executed = %f. Bid(t=%f): %s, Ask(t=%f): %s" % (price_executed,
                                                                              bid.accept_time,
                                                                              str(bid.price),
                                                                              ask.accept_time,
                                                                              str(ask.price)))


            # Either bid or ask side can be partial before and after this matching. Update accordingly
            size_executed = self.transaction_calculator.get_size_executed(bid, ask)
            self._execute(bid, ask, price_executed, size_executed)
            return True, [bid, ask]
        else:
            self.debug('Match(MvsM): Re-enqueue orders')
            self.queue_operator.push(bid)
            self.queue_operator.push(ask)
            return False, [bid, ask]

    def cancel(self, order):
        """
        (a, b)
        Tries to cancel an order corresponding to order, following the Rules:
            1. If order does not match any active order, the order is Rejected
        :return: LOBTableNotification
        """
        # Look up accepted order in bid/ask table by id. If match, execute the cancelation. Else, Reject the order
        # Check bid
        matched_bid_ok, matched_bid = self.queue_operator.pop_bid_by_id(order.m_orderId)
        if matched_bid_ok:
            if matched_bid.get_status() is not OrderStatus.Expired:
                self.debug('Cancel order %i: Success' % matched_bid.m_orderId)
                matched_bid.cancel(self.table.get_current_time())
                order.cancel(self.table.get_current_time())
                return LOBTableNotification(canceled=[matched_bid], completed=[order])
            elif matched_bid.get_status() is OrderStatus.Expired:
                self.debug('Cancel order %i: Fail (order to cancel expired)' % matched_bid.m_orderId)
                order.reject(self.table.get_current_time())
                return LOBTableNotification(expired=[matched_bid], rejected=[order])
            else:
                raise Exception('Case not considered.')
        # Check ask
        matched_ask_ok, matched_ask = self.queue_operator.pop_ask_by_id(order.m_orderId)
        if matched_ask_ok:
            if matched_ask.get_status() is not OrderStatus.Expired:
                self.debug('Cancel order %i: Success' % matched_ask.m_orderId)
                matched_ask.cancel(self.table.get_current_time())
                order.cancel(self.table.get_current_time())
                return LOBTableNotification(canceled=[matched_ask], completed=[order])
            elif matched_ask.get_status() is OrderStatus.Expired:
                self.debug('Cancel order %i: Fail (order to cancel expired)' % matched_ask.m_orderId)
                order.reject(self.table.get_current_time())
                return LOBTableNotification(expired=[matched_ask], rejected=[order])
            else:
                raise Exception('Case not considered (matched ask). Should not happen')
        else:
            self.debug('Cancellation Rejected: order %i not in lob table' % order.m_orderId)
            order.reject(self.table.get_current_time())
            return LOBTableNotification(rejected=[order])

    def _execute(self, bid, ask, price_executed, size_executed):
        """
        Forward execution parameters to each leg of the trade. Update stop orders
        :param bid: Order
        :param ask: Order
        :param price_executed: Float
        :param size_executed: Integer
        :return: 0
        """
        self.debug("Execute: %i vs. %i" % (bid.m_orderId, ask.m_orderId))
        bid.execute_order(self.table.current_time, price_executed, size_executed)
        ask.execute_order(self.table.current_time, price_executed, size_executed)
        if self.table.keep_partials and bid.size_remaining < ask.size_remaining:
            self.debug("Complete Match %s & Partial %s => %f" % (ask.format_str(), bid.format_str(), price_executed))
            self.queue_operator.push(ask)
        elif self.table.keep_partials and bid.size_remaining > ask.size_remaining:
            self.debug("Complete Match %s & Partial %s" % (bid.format_str(), ask.format_str()))
            self.queue_operator.push(bid)
        elif self.table.keep_partials:
            self.debug("Complete Match %s & Complete %s => %f" % (ask.format_str(), bid.format_str(), price_executed))
        else:
            raise Exception('Not considered for now')
        # Keep track of matched orders, with price and size of execution. Process stop queue => market & limit queues
        self.process_stop_queue(price_executed, size_executed)
        return 0

    def process_stop_queue(self, price_executed, size_executed):
        self.debug("process_stop_queue")
        assert(len(self.table.expired_not_notified) == 0)
        stop_new = []
        for order in self.table.stop:
            if self.table.order_checker.checked_expired(order).status == OrderStatus.Expired:
                self.debug('Expired order: %i' % order.m_orderId)
            else:
                # self.debug("Consider updating stop queue")
                change_queue = order.mutate_exec_type(price_executed, size_executed)
                if change_queue:
                    self.debug("Remove order %i from stop queue" % order.m_orderId)
                    self.queue_operator.push(order)
                else:
                    self.debug("Append order %i to stop queue" % order.m_orderId)
                    stop_new.append(order)
        # Update stop table
        self.table.stop = stop_new
        # Return True if some order was unqueued from 'stop'
        return bool(stop_new != [])

    def process_accepted(self, last_order):
        self.debug("Process accept order %i" % last_order.m_orderId)
        notification = LOBTableNotification(accepted=[last_order])
        self.table.update_history_order_notification(last_order, notification)
        return notification

    def process_matching(self, last_order):
        """
        Executes all the possible pair of matching orders in the bid and ask tables. Updates on the fly all the status.
        It returns a notification with information on all the orders that were affected during the matchings
        :param last_order: Order
        :return: LOBTableNotification
        """
        map_notifications = {last_order.m_orderId: last_order}
        matching = True
        while matching:
            # Check the possibility exist of at least matching one pair of orders (read from all required queues)
            if self.queue_operator.ask_empty() or self.queue_operator.bid_empty():
                self.debug('Bid/Ask queues are empty: %r & %r' % (self.queue_operator.bid_empty(), self.queue_operator.ask_empty()))
                break
            else:
                # Fetch first bid and ask in queue
                best_bid = self.queue_operator.best_bid()
                best_ask = self.queue_operator.best_ask()
                if best_bid.get_status() is OrderStatus.Expired:
                    self.debug("Order %i has expired. Dequeing" % best_bid.m_orderId)
                    assert(best_bid.m_orderId != last_order.m_orderId)
                    self.queue_operator.pop_bid()
                    map_notifications[best_bid.m_orderId] = best_bid
                # Check Ask expiration (dequeue if expired)
                if best_ask.get_status() is OrderStatus.Expired:
                    self.debug("Order %i has expired. Dequeing" % best_ask.m_orderId)
                    assert(best_ask.m_orderId != last_order.m_orderId)
                    self.queue_operator.pop_ask()
                    map_notifications[best_ask.m_orderId] = best_ask
                # Check if best_bid or best_ask didn't expire yet
                if best_bid.get_status() is OrderStatus.Expired or best_ask.get_status() is OrderStatus.Expired:
                    # Keep checking for expirations until they are all dequeued
                    continue
                else:
                    # Match best bid and best ask. If one change happened (bid ask spread > 0), notify
                    matching, bid_ask = self.match()
                    bid_notified, ask_notified = bid_ask
                    self.debug("Matching = %r (%i vs. %i)" % (matching, bid_notified.m_orderId, ask_notified.m_orderId))
                    if matching is True:
                        self.debug("New match notification: <%i,%i>" % (bid_notified.m_orderId, ask_notified.m_orderId))
                        map_notifications[bid_notified.m_orderId] = bid_notified
                        map_notifications[ask_notified.m_orderId] = ask_notified
                    else:
                        self.debug("New no match notification: <(%i,%s),(%i,%s)>" % (
                            bid_notified.m_orderId, bid_notified.status.name, ask_notified.m_orderId, ask_notified.status.name))

        # Generate notification from map_notifications
        notification = LOBTableNotification()
        notification.fill_with_orders(map_notifications.values())
        notification.append(expired=self.table.expired_not_notified)
        # Update information about order=>notification history
        self.table.expired_not_notified = []
        self.table.update_history_order_notification(last_order, notification)
        if len(notification.completed) > 0:
            self.debug("Matching algorithm: orders complete: %s" % str([o.m_orderId for o in notification.completed]))

        return notification
