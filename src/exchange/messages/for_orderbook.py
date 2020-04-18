from src.exchange.messages.message_base import Message


class MessageForOrderbook(Message):
    """
    Message class: used by Regulator and Journal. This message must always be from an agent
    """
    def __init__(self, agent, time_sent=None, value=None):
        super(MessageForOrderbook, self).__init__(time_sent, value)
        self.agent = agent

    def __str__(self):
        return 'Message for orderbook: %s' % self.value

    def __repr__(self):
        return self.__str__()