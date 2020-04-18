from src.exchange.notifications.ob_notification import OBNotification


class MarketStatusNotification(OBNotification):
    def __init__(self, execution_information):
        super(MarketStatusNotification, self).__init__(ob_information=execution_information,
                                                       completed=None, partial_completed=None,
                                                       expired=None, accepted=None, rejected=None,
                                                       canceled=None, matched=None)
