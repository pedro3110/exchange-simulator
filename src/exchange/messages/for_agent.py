from src.exchange.messages.message_base import Message


class MessageForAgent(Message):
    """
    Message class: used by Regulator and Journal
    """
    def __init__(self, time_sent, value):
        super(MessageForAgent, self).__init__(time_sent, value)
