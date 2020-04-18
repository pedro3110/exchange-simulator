import numpy as np
from src.exchange.messages.for_orderbook import MessageForOrderbook
from src.exchange.messages.for_agent import MessageForAgent
from src.utils.debug import Debug
from src.strategies.strategy import Strategy
from src.exchange.notifications.ob_notification import OBNotification
from src.exchange.orders.order_creator import OrderCreator
from src.exchange.notifications.market_status_notification import MarketStatusNotification
from src.exchange.notifications.order_status_notification import OrderStatusNotification
from src.exchange.orders.order_utils import OrderStatus
from src.utils.rounding import eq_rounded
import heapq


class PendingOrder:
    def __init__(self, identifier, order, wakeup_time):
        self.identifier = identifier
        self.wakeup_time = wakeup_time
        self.order = order

    def __lt__(self, other):
        return self.wakeup_time < other.wakeup_time


class SpreadGeneratorVersion1(Strategy, Debug):
    def __init__(self, agent, identifier, size_orders, delta_price, max_orders, end_time):
        super(SpreadGeneratorVersion1, self).__init__(agent)
        self.identifier = identifier
        self.size_orders = size_orders
        self.delta_price = delta_price
        self.end_time = end_time

        self.time_advance = float('inf')
        self.next_wakeup_time = float('inf')

        self.max_orders_sent = max_orders
        self.orders_sent = []
        self.contracts = ['INTC']
        self.bid_ask_history = self.reset_bid_ask_history()

        self.last_price_ask = None
        self.last_price_bid = None

        self.next_orders_delivery = {'INTC': []}
        self.leg_status = {
            0: True,  # initialization
            1: False,
            2: False
        }
        self.leg_sequence = {
            0: 1,  # initialization
            1: 2, 2: 1
        }
        self.active_leg = 0
        self.active_leg_status_orders = {}
        self.prepared_order = None

    def reset_bid_ask_history(self):
        return {
            contract: {
                'bid': None,
                'ask': None
            } for contract in self.contracts}

    def output_function(self, current_time, elapsed):
        output = {}
        for contract in self.contracts:
            pending_orders = self.next_orders_delivery[contract]
            if len(pending_orders) > 0:
                next_pending_order = heapq.heappop(pending_orders)
                assert (current_time + elapsed <= next_pending_order.wakeup_time)
                self.debug('Check pending order: %f %f %f' % (current_time, elapsed, next_pending_order.wakeup_time))
                if eq_rounded(current_time + elapsed, next_pending_order.wakeup_time):
                    next_order = next_pending_order.order
                    self.debug("Order ready: %s" % str(next_order))
                    self.orders_sent.append(next_order.m_orderId)
                    output['out_order'] = MessageForOrderbook(self.identifier, current_time + elapsed, next_order)
                    break
                else:
                    self.debug("Pending Order not ready: %f %f %f" % (current_time, elapsed, next_pending_order.wakeup_time))
                    heapq.heappush(self.next_orders_delivery[contract], next_pending_order)
        # Emit output
        return output

    def get_prepared_order(self, current_time, elapsed):
        self.debug("get_prepared_order")
        if self.prepared_order is None:
            return False, None
        else:
            return True, self.prepared_order

    def update_order_notification(self, notification):
        self.debug("update_order_notification")
        super(SpreadGeneratorVersion1, self).update_strategy_orders_status(notification)
        for order_id, status in self.get_orders_status().items():
            # self.debug(str(order_id))
            # self.debug(str(self.orders_sent))
            # self.debug(str(self.active_leg_status_orders))
            # assert order_id in self.active_leg_status_orders
            self.active_leg_status_orders[order_id] = status

        # Update status if all orders of active leg are complete
        # self.debug(str(self.active_leg_status_orders))
        if all([status == OrderStatus.Complete for status in self.active_leg_status_orders.values()]):
            self.leg_status[self.active_leg] = True
        # Return
        return True

    def update_market_information(self, notification):
        self.debug("update_market_information")
        if isinstance(notification, OBNotification):
            self.debug(str(notification))
            contract = notification.get_contract()
            for k, v in notification.get_best_bid_ask_price_and_size().items():
                if v is not None:
                    if k == 'bid' and v['price'] != self.last_price_bid:
                        self.bid_ask_history[contract][k] = v
                    if k == 'ask' and v['price'] != self.last_price_ask:
                        self.bid_ask_history[contract][k] = v
            return True
        else:
            raise Exception('Can only process OBNotifications for now')

    def process_in_notify_order(self, current_time, elapsed, message):
        self.debug("process_in_notify_order")
        assert (isinstance(message.value, OrderStatusNotification))
        if isinstance(message, MessageForAgent):
            notification = message.value
            assert (isinstance(notification, OBNotification))
            self.update_order_notification(notification)
            self.schedule_order_if_needed(current_time, elapsed)
        # Go to output + internal transition
        return 0

    def process_in_next(self, current_time, elapsed, message):
        self.debug("process_in_next")
        self.debug(str(message.value))
        assert (isinstance(message.value, MarketStatusNotification))
        if isinstance(message, MessageForAgent):
            notification = message.value
            self.update_market_information(notification)
            self.schedule_order_if_needed(current_time, elapsed)
        # Go to output + internal transition
        return 0

    def process_internal(self, current_time, elapsed):
        self.debug("process_internal")
        self.schedule_order_if_needed(current_time, elapsed)
        # Only reactive to external transitions
        waiting_time = float('inf')
        for contract in self.next_orders_delivery:
            if len(self.next_orders_delivery[contract]) > 0:
                self.debug("push into next_orders_delivery")
                pending_order = heapq.heappop(self.next_orders_delivery[contract])
                assert (pending_order.wakeup_time <= current_time + elapsed)
                wt = pending_order.wakeup_time - current_time - elapsed
                waiting_time = min(waiting_time, wt)
                heapq.heappush(self.next_orders_delivery[contract], pending_order)
        # Wait as much time as necessary for next order prepared (scheduled on every external transition. Another
        # option is to also check regularly in the internal transitions scheduled, but that is not necessary for now)
        return waiting_time

    def schedule_order_if_needed(self, current_time, elapsed):
        self.debug("schedule order if needed (1)")
        # Analyze market information about each contract
        for contract_information in ['bid', 'ask']:
            for contract in ['INTC']:
                if self.bid_ask_history[contract][contract_information] is None:
                    self.debug("bid_ask_history not complete")
                    self.debug(str(self.bid_ask_history))
                    return None
        spread = self.bid_ask_history['INTC']['ask']['price'] - self.bid_ask_history['INTC']['bid']['price']

        # Condition to send a new order: TODO: limit by cash and size
        if spread < 30 and len(self.orders_sent) < self.max_orders_sent:
            self.prepare_next_order_if_necessary(current_time, elapsed, self.active_leg)
            self.bid_ask_history = self.reset_bid_ask_history()
        return None

    def prepare_next_order_if_necessary(self, current_time, elapsed, active_leg):
        self.debug("prepare_next_order_if_necessary. Leg = %i" % active_leg)

        # SET PRICES
        price_intc_ask = self.bid_ask_history['INTC']['bid']['price'] - self.delta_price
        # size_intc_ask = self.bid_ask_history['INTC']['ask']['size']
        size_intc_ask = self.size_orders

        price_intc_bid = self.bid_ask_history['INTC']['ask']['price'] + self.delta_price
        # size_intc_bid = self.bid_ask_history['INTC']['bid']['size']
        size_intc_bid = self.size_orders

        self.last_price_ask = price_intc_ask
        self.last_price_bid = price_intc_bid

        # ORDER 1
        order_intc_ask = OrderCreator.create_order_from_dict({
            'contract': 'INTC', 'creator_id': self.identifier, 'order_id': np.random.randint(0, 1000),
            'price': price_intc_ask, 'size': size_intc_ask, 'direction': -1, 'exec_type': 0,
            'creation_time': current_time + elapsed, 'expiration_time': float('inf')
        })
        pending_order_intc_ask = PendingOrder(identifier=order_intc_ask.m_orderId, order=order_intc_ask,
                                              wakeup_time=current_time + elapsed)  # IMMEDIATE SEND

        # ORDER 2
        order_intc_bid = OrderCreator.create_order_from_dict({
            'contract': 'INTC', 'creator_id': self.identifier, 'order_id': np.random.randint(0, 1000),
            'price': price_intc_bid, 'size': size_intc_bid, 'direction': 1, 'exec_type': 0,
            'creation_time': current_time + elapsed, 'expiration_time': float('inf')
        })
        pending_order_intc_bid = PendingOrder(identifier=order_intc_ask.m_orderId, order=order_intc_bid,
                                              wakeup_time=current_time + elapsed)  # IMMEDIATE SEND

        # Enqueue ORDER 1 + 2
        self.debug("Enqueue orders: %i %i" % (order_intc_bid.m_orderId, order_intc_ask.m_orderId))
        heapq.heappush(self.next_orders_delivery['INTC'], pending_order_intc_ask)
        heapq.heappush(self.next_orders_delivery['INTC'], pending_order_intc_bid)
        self.active_leg_status_orders = {
            order_intc_ask.m_orderId: order_intc_ask.status,
            order_intc_bid.m_orderId: order_intc_bid.status
        }
        return None
