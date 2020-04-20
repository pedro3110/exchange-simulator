from src.exchange.orderbook.limit_order_book.helpers.lob_notification import LOBTableNotification
from src.utils.ifnonizer import ifnonizer


class OBNotification(object):
    """
    Every OB can emit notifications with all the information needed to understand the updation in it's internal state
    """
    def __init__(self, ob_information=None, completed=None, partial_completed=None, expired=None,
                 accepted=None, rejected=None, canceled=None, matched=None):
        self.ob_information = ob_information
        self.completed = ifnonizer(completed, [])
        self.partial_completed = ifnonizer(partial_completed, [])
        self.expired = ifnonizer(expired, [])
        self.accepted = ifnonizer(accepted, [])
        self.rejected = ifnonizer(rejected, [])
        self.canceled = ifnonizer(canceled, [])
        self.matched = ifnonizer(matched, [])

    def get_ob_information(self):
        return self.ob_information

    def get_completed(self):
        return self.completed

    def get_partial_completed(self):
        return self.partial_completed

    def get_expired(self):
        return self.expired

    def get_accepted(self):
        return self.accepted

    def get_rejected(self):
        return self.rejected

    def get_canceled(self):
        return self.canceled

    def get_matched(self):
        return self.matched

    def get_contract(self):
        return self.ob_information.get_contract()

    def get_best_ask_price(self):
        return self.ob_information.get_best_ask_price() if self.ob_information is not None else None

    def get_best_bid_ask_price_and_size(self):
        return self.ob_information.get_best_bid_ask_price_and_size() if self.ob_information is not None else None


class OBNotificationCreator:
    """
    Used to create LOBTableNotification from OBNotification
    """
    @staticmethod
    def create_from_batable_notification(lob_notification, bat_information):
        assert(isinstance(lob_notification, LOBTableNotification))
        return OBNotification(
            ob_information=bat_information,
            completed=lob_notification.completed,
            partial_completed=lob_notification.partial_completed,
            expired=lob_notification.expired,
            accepted=lob_notification.accepted,
            rejected=lob_notification.rejected,
            canceled=lob_notification.canceled,
            matched=lob_notification.matched
        )
