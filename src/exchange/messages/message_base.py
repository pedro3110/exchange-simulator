from src.utils.rounding import rounded


class Message(object):
    def __init__(self, time_sent=None, value=None):
        self.value = value
        self.time_sent = rounded(time_sent)

    def set_time_sent(self, time_sent):
        self.time_sent = time_sent
        return self.time_sent
