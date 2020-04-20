from src.exchange.messages.message_base import Message


class MessageForJournal(Message):
    """
    Message class: used by orderbook.
    """
    def __init__(self, time_sent, value, notifications=None):
        super(MessageForJournal, self).__init__(time_sent, value)
        # self.time_sent = time_sent
        self.notifications = notifications

    def __str__(self):
        return 'Message for journal: %s' % self.value

    def __repr__(self):
        return self.__str__()