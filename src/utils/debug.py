import logging


class Debug(object):

    logger_debug = logging.getLogger('')
    logger_debug.setLevel(logging.DEBUG)

    # def __init__(self):
    #
    #     # self.logger_info = logging.getLogger('')
    #      #self.logger_info.setLevel(logging.INFO)
    #
    #     # if formatter is None:
    #     #     formatter = logging.Formatter('%(name)s : %(message)s')
    #     # file_handler = logging.FileHandler(filename)
    #     # file_handler.setFormatter(formatter)
    #     # self.logger.addHandler(file_handler)

    def get_identifier(self):
        raise NotImplemented()

    # def get_info(self):
    #     return self.logger_info

    def debug(self, msg):
        Debug.logger_debug.debug(self.get_identifier() + ":" + msg)

    # def info(self, msg):
    #     self.logger_debug.debug(self.get_identifier() + ":" + msg)
