from src.exchange.notifications.ob_notification import OBNotification


class OrderStatusNotification(OBNotification):
    def __init__(self, completed=None, partial_completed=None, expired=None,
                 accepted=None, rejected=None, canceled=None, matched=None):
        # logger.debug(accepted)
        # logger.debug(partial_completed)
        super(OrderStatusNotification, self).__init__(ob_information=None,
                                                      completed=completed, partial_completed=partial_completed,
                                                      expired=expired, accepted=accepted, rejected=rejected,
                                                      canceled=canceled, matched=matched)

    def extend(self, other):
        self.completed += other.completed
        self.partial_completed += other.partial_completed
        self.expired += other.expired
        self.accepted += other.accepted
        self.rejected += other.rejected
        self.canceled += other.canceled
        self.matched += other.matched
        return self
