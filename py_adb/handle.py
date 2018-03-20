import logging
from handlers.usb_handler import UsbHandler

logger = logging.getLogger(__name__)


class HandlerFactory(object):
    DEFAULT_HANDLER = 'usb'

    def __init__(self):
        self.handlers = {
            'usb': ('usb:', UsbHandler)
        }

    def get_handler(self, source):
        for name, signature in self.handlers.items():
            if source.startswith(signature[0]):
                return signature[1](source)
        else:
            logger.info('Handler not found in known handlers, using default: %s', self.DEFAULT_HANDLER)
            return self.handlers[self.DEFAULT_HANDLER][1](source)
