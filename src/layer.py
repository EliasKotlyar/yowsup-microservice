from yowsup.layers.interface import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers import YowLayerEvent, EventCallback
from yowsup.layers.network import YowNetworkLayer
import sys
from yowsup.common import YowConstants
import datetime
import os
import logging
from yowsup.layers.protocol_groups.protocolentities import *
from yowsup.layers.protocol_presence.protocolentities import *
from yowsup.layers.protocol_messages.protocolentities import *
from yowsup.layers.protocol_ib.protocolentities import *
from yowsup.layers.protocol_iq.protocolentities import *
from yowsup.layers.protocol_contacts.protocolentities import *
from yowsup.layers.protocol_chatstate.protocolentities import *
from yowsup.layers.protocol_privacy.protocolentities import *
from yowsup.layers.protocol_media.protocolentities import *
from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_profiles.protocolentities import *
from yowsup.common.tools import Jid
from yowsup.common.optionalmodules import PILOptionalModule, AxolotlOptionalModule

logger = logging.getLogger(__name__)


class SendReciveLayer(YowInterfaceLayer):
    PROP_RECEIPT_AUTO = "org.openwhatsapp.yowsup.prop.cli.autoreceipt"
    PROP_RECEIPT_KEEPALIVE = "org.openwhatsapp.yowsup.prop.cli.keepalive"
    PROP_CONTACT_JID = "org.openwhatsapp.yowsup.prop.cli.contact.jid"
    EVENT_LOGIN = "org.openwhatsapp.yowsup.event.cli.login"
    EVENT_START = "org.openwhatsapp.yowsup.event.cli.start"
    EVENT_SENDANDEXIT = "org.openwhatsapp.yowsup.event.cli.sendandexit"

    MESSAGE_FORMAT = "[{FROM}({TIME})]:[{MESSAGE_ID}]\t {MESSAGE}"

    FAIL_OPT_PILLOW = "No PIL library installed, try install pillow"
    FAIL_OPT_AXOLOTL = "axolotl is not installed, try install python-axolotl"

    DISCONNECT_ACTION_PROMPT = 0
    DISCONNECT_ACTION_EXIT = 1

    ACCOUNT_DEL_WARNINGS = 4
    EVENT_SEND_MESSAGE = "org.openwhatsapp.yowsup.prop.queue.sendmessage"
    
    def __init__(self):
        super(SendReciveLayer, self).__init__()
        YowInterfaceLayer.__init__(self)
        self.accountDelWarnings = 0
        self.connected = False
        self.username = None
        self.sendReceipts = True
        self.sendRead = True
        self.disconnectAction = self.__class__.DISCONNECT_ACTION_PROMPT

        self.credentials = None
        

        # add aliases to make it user to use commands. for example you can then do:
        # /message send foobar "HI"
        # and then it will get automaticlaly mapped to foobar's jid
        self.jidAliases = {
            # "NAME": "PHONE@s.whatsapp.net"
        }

    def aliasToJid(self, calias):

        jid = "%s@s.whatsapp.net" % calias
        return jid

    def jidToAlias(self, jid):
        for alias, ajid in self.jidAliases.items():
            if ajid == jid:
                return alias
        return jid

    def setCredentials(self, username, password):
        self.getLayerInterface(YowAuthenticationProtocolLayer).setCredentials(username, password)

        return "%s@s.whatsapp.net" % username

    @EventCallback(EVENT_START)
    def onStart(self, layerEvent):
        #self.startInput()
        return True

    @EventCallback(EVENT_SENDANDEXIT)
    def onSendAndExit(self, layerEvent):
        credentials = layerEvent.getArg("credentials")
        target = layerEvent.getArg("target")
        message = layerEvent.getArg("message")
        self.sendMessageAndDisconnect(credentials, target, message)
        return True

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def onStateDisconnected(self, layerEvent):
        self.output("Disconnected: %s" % layerEvent.getArg("reason"))
        if self.disconnectAction == self.__class__.DISCONNECT_ACTION_PROMPT:
            self.connected = False
            # self.notifyInputThread()
        else:
            os._exit(os.EX_OK)

    def assertConnected(self):
        if self.connected:
            return True
        else:
            self.output("Not connected", tag="Error", prompt=False)
            return False

    #### batch cmds #####
 #   def sendMessageAndDisconnect(self, credentials, jid, message):
 #       self.disconnectAction = self.__class__.DISCONNECT_ACTION_EXIT
 #       self.queueCmd("/login %s %s" % credentials)
 #       self.queueCmd("/message send %s \"%s\" wait" % (jid, message))
 #       self.queueCmd("/disconnect")
 #       self.startInput()

    ######## receive #########

    @ProtocolEntityCallback("chatstate")
    def onChatstate(self, entity):
        print(entity)

    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        print(entity)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        self.toLower(entity.ack())

    @ProtocolEntityCallback("ack")
    def onAck(self, entity):
        # formattedDate = datetime.datetime.fromtimestamp(self.sentCache[entity.getId()][0]).strftime('%d-%m-%Y %H:%M')
        # print("%s [%s]:%s"%(self.username, formattedDate, self.sentCache[entity.getId()][1]))
        if entity.getClass() == "message":
            self.output(entity.getId(), tag="Sent")
            # self.notifyInputThread()

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        self.connected = True
        self.output("Logged in!", "Auth", prompt=False)
        # self.notifyInputThread()

    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        self.connected = False
        self.output("Login Failed, reason: %s" % entity.getReason(), prompt=False)

    @ProtocolEntityCallback("notification")
    def onNotification(self, notification):
        notificationData = notification.__str__()
        if notificationData:
            self.output(notificationData, tag="Notification")
        else:
            self.output("From :%s, Type: %s" % (self.jidToAlias(notification.getFrom()), notification.getType()),
                        tag="Notification")
        if self.sendReceipts:
            self.toLower(notification.ack())

    @ProtocolEntityCallback("message")
    def onMessage(self, message):
        messageOut = ""
        if message.getType() == "text":
            # self.output(message.getBody(), tag = "%s [%s]"%(message.getFrom(), formattedDate))
            messageOut = self.getTextMessageBody(message)
        elif message.getType() == "media":
            messageOut = self.getMediaMessageBody(message)
        else:
            messageOut = "Unknown message type %s " % message.getType()
            print(messageOut.toProtocolTreeNode())

        formattedDate = datetime.datetime.fromtimestamp(message.getTimestamp()).strftime('%d-%m-%Y %H:%M')
        sender = message.getFrom() if not message.isGroupMessage() else "%s/%s" % (
            message.getParticipant(False), message.getFrom())
        output = self.__class__.MESSAGE_FORMAT.format(
            FROM=sender,
            TIME=formattedDate,
            MESSAGE=messageOut.encode('latin-1').decode() if sys.version_info >= (3, 0) else messageOut,
            MESSAGE_ID=message.getId()
        )

        self.output(output, tag=None, prompt=not self.sendReceipts)
        if self.sendReceipts:
            self.toLower(message.ack(self.sendRead))
            self.output("Sent delivered receipt" + " and Read" if self.sendRead else "",
                        tag="Message %s" % message.getId())

    @EventCallback(EVENT_SEND_MESSAGE)
    def doSendMEssage(self, layerEvent):
        content = layerEvent.getArg("msg")
        number = layerEvent.getArg("number")
        self.output("Send Message to %s : %s" % (number, content))
        jid = number

        if self.assertConnected():
            outgoingMessage = TextMessageProtocolEntity(
                content.encode("utf-8") if sys.version_info >= (3, 0) else content, to=self.aliasToJid(number))
            self.toLower(outgoingMessage)




    def getTextMessageBody(self, message):
        return message.getBody()

    def getMediaMessageBody(self, message):
        if message.getMediaType() in ("image", "audio", "video"):
            return self.getDownloadableMediaMessageBody(message)
        else:
            return "[Media Type: %s]" % message.getMediaType()

    def getDownloadableMediaMessageBody(self, message):
        return "[Media Type:{media_type}, Size:{media_size}, URL:{media_url}]".format(
            media_type=message.getMediaType(),
            media_size=message.getMediaSize(),
            media_url=message.getMediaUrl()
        )

    def doSendMedia(self, mediaType, filePath, url, to, ip=None, caption=None):
        if mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE:
            entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption=caption)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO:
            entity = AudioDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_VIDEO:
            entity = VideoDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption=caption)
        self.toLower(entity)

    def __str__(self):
        return "CLI Interface Layer"

    ########### callbacks ############

    def onRequestUploadResult(self, jid, mediaType, filePath, resultRequestUploadIqProtocolEntity,
                              requestUploadIqProtocolEntity, caption=None):

        if resultRequestUploadIqProtocolEntity.isDuplicate():
            self.doSendMedia(mediaType, filePath, resultRequestUploadIqProtocolEntity.getUrl(), jid,
                             resultRequestUploadIqProtocolEntity.getIp(), caption)
        else:
            successFn = lambda filePath, jid, url: self.doSendMedia(mediaType, filePath, url, jid,
                                                                    resultRequestUploadIqProtocolEntity.getIp(),
                                                                    caption)
            mediaUploader = MediaUploader(jid, self.getOwnJid(), filePath,
                                          resultRequestUploadIqProtocolEntity.getUrl(),
                                          resultRequestUploadIqProtocolEntity.getResumeOffset(),
                                          successFn, self.onUploadError, self.onUploadProgress, async=False)
            mediaUploader.start()

    def onRequestUploadError(self, jid, path, errorRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity):
        logger.error("Request upload for file %s for %s failed" % (path, jid))

    def onUploadError(self, filePath, jid, url):
        logger.error("Upload file %s to %s for %s failed!" % (filePath, url, jid))

    def onUploadProgress(self, filePath, jid, url, progress):
        sys.stdout.write("%s => %s, %d%% \r" % (os.path.basename(filePath), jid, progress))
        sys.stdout.flush()

    def onGetContactPictureResult(self, resultGetPictureIqProtocolEntiy, getPictureIqProtocolEntity):
        # do here whatever you want
        # write to a file
        # or open
        # or do nothing
        # write to file example:
        # resultGetPictureIqProtocolEntiy.writeToFile("/tmp/yowpics/%s_%s.jpg" % (getPictureIqProtocolEntity.getTo(), "preview" if resultGetPictureIqProtocolEntiy.isPreview() else "full"))
        pass

    def __str__(self):
        return "Send Recive Interface Layer"

    def output(self, str, tag="", prompt=""):

        # print(str)
        logging.info(str)
        pass
