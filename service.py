from nameko.rpc import rpc
import logging

from pprint import pprint
from src.yowsupextension import YowsupExtension
from nameko.timer import timer

class yowsup(object):
    name = "yowsup"

    y = YowsupExtension()

    @rpc
    def send(self, type, body, address):
        logging.info('Get message: %s,%s,%s' % (type, body, address))
        if(type == "simple"):
            output = self.y.sendTextMessage(address, body)
        elif(type == "media"):
            output = self.y.sendMediaMessage(address, body)

        return True
        #pprint(self)
        #logging.info(self.y)
        #output = self.y.sendCommand('Test')
        #logging.info(output)

