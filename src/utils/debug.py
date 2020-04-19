import logging
import sys, os
from config import log_path


class Debug(object):

    logger_info = logging.getLogger("info")
    logger_info.setLevel(logging.INFO)
    logger_debug = logging.getLogger('debug')
    logger_debug.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(message)s')
    file_handler = logging.FileHandler(log_path + 'all.log')
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger_debug.addHandler(file_handler)
    # logger_debug.addHandler(stdout_handler)

    # Clean files
    for filename in os.listdir(log_path):
        for filename in ['all.log']:
            dirname = "%s%s" % (log_path, filename)
            with open(dirname, 'w+') as f:
                f.truncate()

    def get_identifier(self):
        raise NotImplemented()

    def get_info(self):
        return self.logger_info

    def debug(self, msg):
        Debug.logger_debug.debug("%s : %s" % (self.get_identifier(), msg))

    def info(self, msg):
        Debug.logger_debug.info("%s : %s" % (self.get_identifier(), msg))
