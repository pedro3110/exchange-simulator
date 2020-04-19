from pypdevs.DEVS import AtomicDEVS
from src.utils.debug import Debug
from src.exchange.messages.for_journal import MessageForJournal
from src.exchange.orderbook.limit_order_book.lobtable import LOBTable
from src.exchange.notifications.ob_information import OBInformation
from src.exchange.notifications.ob_notification import OBNotificationCreator
from src.utils.rounding import rounded, eq_rounded, lt_rounded
from src.utils.decorators import approximating_time_advance
from src.exchange.base_orderbook import OrderbookBase
import heapq


class OrderbookVersion1(OrderbookBase, Debug):
    def __init__(self, identifier, contract, delay_order, delay_notification):
        AtomicDEVS.__init__(self, identifier)
        self.identifier = identifier
        self.contract = contract
        self.tick_size = None

        self.last_current_time = 0.0
        self.time_advance = float('inf')

        self.last_transition = None  # [internal, external]
        self.last_elapsed = 0.0

        self.in_order = self.addInPort('in_order')
        self.out_journal = self.addOutPort('out_journal')
        output_ports_map = {'out_journal': self.out_journal}
        self.strategy = OrderbookStrategy(self, identifier, contract, delay_order, delay_notification, output_ports_map)


    def set_tick_size(self, tick_size):
        self.tick_size = tick_size


class PendingNotification:
    def __init__(self, identifier, notification, wakeup_time):
        self.identifier = identifier
        self.wakeup_time = wakeup_time
        self.notification = notification

    def __lt__(self, other):
        return self.wakeup_time < other.wakeup_time


class PendingOrder:
    def __init__(self, identifier, order, wakeup_time):
        self.identifier = identifier
        self.wakeup_time = wakeup_time
        self.order = order

    def __lt__(self, other):
        return self.wakeup_time < other.wakeup_time


class OrderbookStrategy(Debug):
    def __init__(self, agent, identifier, contract, delay_order, delay_notification, output_ports_map):
        self.agent = agent
        self.identifier = identifier + '_strategy'
        self.last_message_id = 0
        self.output_ports_map = output_ports_map

        self.contract = contract
        self.bid_ask_table = LOBTable(contract=contract)

        # Priority queue of orders to process
        self.delay_order = delay_order
        self.delay_notification = delay_notification
        self.ready = []

        self.next_order_status_delivery = {contract: []}
        self.next_notification_delivery = {contract: []}

    def get_identifier(self):
        return self.identifier

    def get_next_message_id(self):
        self.last_message_id += 1
        return self.last_message_id

    def set_initial_orders(self, initial_orders):
        return self.bid_ask_table.set_initial_orders(initial_orders)

    def set_tick_size(self, tick_size):
        self.bid_ask_table.set_tick_size(tick_size)
        return 0

    def output_function(self, current_time, elapsed):
        output = {}
        for out_port in ['out_journal']:
            # Look for a notification for each LOB table
            messages = self.next_notification_delivery[self.contract]
            if len(messages) > 0:
                next_message = heapq.heappop(messages)
                assert(current_time + elapsed <= next_message.wakeup_time)
                self.debug('Check notification: %f %f %f' % (current_time, elapsed, next_message.wakeup_time))
                self.debug(str(next_message))
                if eq_rounded(current_time + elapsed, next_message.wakeup_time):
                    self.debug("Notification ready")
                    bat_notification = next_message.notification
                    ob_information = OBInformation(
                        contract=self.contract,
                        best_ask=self.bid_ask_table.queue_observer.best_ask(),
                        best_bid=self.bid_ask_table.queue_observer.best_bid()
                    )
                    ob_notification = OBNotificationCreator.create_from_batable_notification(bat_notification, ob_information)
                    output[out_port] = MessageForJournal(current_time + elapsed, ob_notification)
                else:
                    self.debug("Notification not ready: %f %f %f" % (current_time, elapsed, next_message.wakeup_time))
                    heapq.heappush(self.next_notification_delivery[self.contract], next_message)

        self.debug("Emit output = %s" % str(output))
        return output

    def get_smallest_wakeup_time_orders_and_notifications(self):
        smallest_wakeup_time = float('inf')
        messages = self.next_notification_delivery[self.contract]
        if len(messages) > 0:
            wakeup_time = heapq.nsmallest(1, messages)[0].wakeup_time
            if wakeup_time < smallest_wakeup_time:
                smallest_wakeup_time = wakeup_time
        # 2.
        messages = self.next_order_status_delivery[self.contract]
        if len(messages) > 0:
            wakeup_time = heapq.nsmallest(1, messages)[0].wakeup_time
            if wakeup_time < smallest_wakeup_time:
                smallest_wakeup_time = wakeup_time
        return smallest_wakeup_time

    def process_internal(self, current_time, elapsed):
        self.debug("process_internal")
        if len(self.next_order_status_delivery[self.contract]) == 0:
            self.debug("No orders missing processing")
            next_wakeup_time = self.get_smallest_wakeup_time_orders_and_notifications()
            self.debug("Next wakeup time = %f" % next_wakeup_time)
            self.debug("Next waiting time = %f" % (next_wakeup_time - current_time - elapsed))
            return next_wakeup_time - current_time - elapsed
        else:
            self.debug("Processing orders")
            top_order = heapq.heappop(self.next_order_status_delivery[self.contract])
            assert(current_time + elapsed <= top_order.wakeup_time)
            if lt_rounded(current_time + elapsed, top_order.wakeup_time):
                # Re-enqueue in order queue
                heapq.heappush(self.next_order_status_delivery[self.contract], top_order)
            else:
                # Process and enqueue in notifications queue
                notification = self.bid_ask_table.handle_order(top_order.order, current_time + elapsed)
                notification_wake_up = current_time + elapsed + self.delay_notification
                heapq.heappush(self.next_notification_delivery[self.contract],
                               PendingNotification(self.get_next_message_id(), notification, notification_wake_up))
            next_wakeup_time = self.get_smallest_wakeup_time_orders_and_notifications()
            self.debug("Next wakeup time = %f" % next_wakeup_time)
            self.debug("Next waiting time = %f" % (next_wakeup_time - current_time - elapsed))
            return next_wakeup_time - current_time - elapsed

    def process_in_order(self, current_time, elapsed, message):
        self.debug("process_in_order")
        wakeup_time = current_time + elapsed + self.delay_order

        self.debug("execution_time=%f, current_time=%f, elapsed=%f, delay=%f" % (wakeup_time, current_time, elapsed, self.delay_order))

        heapq.heappush(self.next_order_status_delivery[message.value.contract],
                       PendingOrder(self.get_next_message_id(), message.value, wakeup_time))
        next_wakeup_time = self.get_smallest_wakeup_time_orders_and_notifications()
        self.debug("Next wakeup time = %f" % next_wakeup_time)
        self.debug("Next waiting time = %f" % (next_wakeup_time - current_time - elapsed))
        return next_wakeup_time - current_time - elapsed
