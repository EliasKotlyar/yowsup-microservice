import pexpect
import logging

from nameko.extensions import DependencyProvider


class YowsupExtension(DependencyProvider):
    def setup(self):
        logging.info('Starting YowsUP...')

        number = self.container.config['YOWSUP_USERNAME']
        password = self.container.config['YOWSUP_PASSWORD']
        logging.info('Trying to connect via %s:%s'  % (number, password))
        startCommand = 'yowsup-cli demos --yowsup --login %s:%s' % (number, password)

        self.shell = pexpect.spawn(startCommand)
        self.expect([".+\[offline\]:"])
        self.shell.sendline("/L")


        return True

    def expect(self,expectArr):
        try:
            i = self.shell.expect(expectArr,timeout=1)
        except:
            logging.info("Exception was thrown")
            logging.info("debug information:")
            logging.info(str(self.shell))
            i = 0
        return i

    def sendTextMessage(self, address,message):
        logging.info('Trying to send Message to %s:%s' % (address, message))
        messageCommand = '/message send %s %s' % (address, message)
        self.shell.sendline(messageCommand)
        return True

    def get_dependency(self, worker_ctx):
        return self
