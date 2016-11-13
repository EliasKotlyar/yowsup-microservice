import queue
import threading

import pexpect
import logging

from nameko.extensions import DependencyProvider
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.protocol_media import YowMediaProtocolLayer
from yowsup.layers import YowLayerEvent
from yowsup.stacks import YowStackBuilder
from yowsup.layers.auth import AuthError

#import Queue.Queue
#from Queue import queue
from axolotl.duplicatemessagexception import DuplicateMessageException

from src.layer import QueueLayer
from yowsup.layers.axolotl.props import PROP_IDENTITY_AUTOTRUST

class YowsupExtension(DependencyProvider):
    def setup(self):
        self.output('Starting YowsUP...')

        number = self.container.config['YOWSUP_USERNAME']
        password = self.container.config['YOWSUP_PASSWORD']

        credentials = (number, password)  # replace with your phone and password

        sendQueue = queue.Queue()

        stackBuilder = YowStackBuilder()
        self.stack = stackBuilder \
            .pushDefaultLayers(True) \
            .push(QueueLayer(sendQueue)) \
            .build()

        # .push(YowMediaProtocolLayer) \



        self.stack.setCredentials(credentials)
        self.stack.setProp(PROP_IDENTITY_AUTOTRUST, True)
        #self.stack.broadcastEvent(YowLayerEvent(YowsupCliLayer.EVENT_START))



        connectEvent = YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT)
        self.stack.broadcastEvent(connectEvent)


        def startThread():
            try:
                self.stack.loop(timeout=0.5, discrete=0.5)
            except AuthError as e:
                self.output("Auth Error, reason %s" % e)
            except KeyboardInterrupt:
                self.output("\nYowsdown KeyboardInterrupt")
                exit(0)
            except Exception as e:
                self.output(e)
                self.output("Whatsapp exited")
                exit(0)

        t1 = threading.Thread(target=startThread)
        t1.daemon = True
        t1.start()





    def sendTextMessage(self, address,message):
        self.output('Trying to send Message to %s:%s' % (address, message))
        messageCommand = '/message send %s "%s"' % (address, message)
        self.stack.broadcastEvent(YowLayerEvent(name=QueueLayer.EVENT_SEND_MESSAGE, msg=message, number=address))
        return True

    def get_dependency(self, worker_ctx):
        return self
    def output(self, str):

        #print(str)
        logging.info(str)
        pass
