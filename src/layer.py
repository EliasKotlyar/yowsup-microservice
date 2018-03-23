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
import urllib.request
import base64
from time import sleep

logger = logging.getLogger(__name__)
STATUS_FILES_DIRECTORY = '/tmp/statuses/'
RECONNECT_TIMEOUT = 2
# set -1 if it has to reconnect until it finally reconnects
RECONNECT_ATTEMPTS = 30

class SendReciveLayer(YowInterfaceLayer):


    MESSAGE_FORMAT = "{{\"from\":\"{FROM}\",\"to\":\"{TO}\",\"time\":\"{TIME}\",\"id\":\"{MESSAGE_ID}\",\"message\":{MESSAGE},\"type\":\"{TYPE}\",\"notify\":\"{NOTIFY}\"}}"

    DISCONNECT_ACTION_PROMPT = 0

    EVENT_SEND_MESSAGE = "org.openwhatsapp.yowsup.prop.queue.sendmessage"
    EVENT_SEND_IMAGE = "org.openwhatsapp.yowsup.prop.queue.sendimage"
    EVENT_SEND_VIDEO = "org.openwhatsapp.yowsup.prop.queue.sendvideo"
    EVENT_SEND_AUDIO = "org.openwhatsapp.yowsup.prop.queue.sendaudio"

    def __init__(self, tokenReSendMessage, urlReSendMessage, myNumber):
        super(SendReciveLayer, self).__init__()
        YowInterfaceLayer.__init__(self)
        self.accountDelWarnings = 0
        self.connected = False
        self.username = None
        self.sendReceipts = True
        self.sendRead = True
        self.disconnectAction = self.__class__.DISCONNECT_ACTION_PROMPT
        self.myNumber = myNumber
        self.credentials = None

        self.tokenReSendMessage = tokenReSendMessage
        self.urlReSendMessage = urlReSendMessage

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
            status_filename = STATUS_FILES_DIRECTORY + 'lock'
            try:
                with open(status_filename, 'w') as file:
                    file.write('success')
            except Exception as e:
                self.output('Could not write to file {}. Exception: {}'.format(status_filename, str(e)))
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
            messageOut = '"' + self.getTextMessageBody(message) + '"'
        elif message.getType() == "media" and message.getMediaType() in ("image", "audio", "video"):
            messageOut = self.getMediaMessageBody(message)
        elif message.getType() == "media" and message.getMediaType() == "location":
            messageOut = self.getLocationMessageBody(message)
        elif message.getType() == "media" and message.getMediaType() == "vcard":
            messageOut = self.getVCardMessageBody(message)                        
        else:
            messageOut = "Unknown message type %s, %s " % (message.getType(),message.getMediaType())

        formattedDate = datetime.datetime.fromtimestamp(message.getTimestamp()).strftime('%Y-%m-%d %H:%M:%S')
        sender = message.getFrom() if not message.isGroupMessage() else "%s/%s" % (
            message.getParticipant(False), message.getFrom())

        # convert message to json
        output = self.__class__.MESSAGE_FORMAT.format(
            FROM=sender,
            TO=self.myNumber,
            TIME=formattedDate,
            MESSAGE=messageOut.encode('utf8').decode() if sys.version_info >= (3, 0) else messageOut,
            MESSAGE_ID=message.getId(),
            TYPE=message.getType(),
            NOTIFY=message.getNotify(),
        )

        req = urllib.request.Request(self.urlReSendMessage)
        req.add_header('Content-Type', 'application/json; charset=utf-8')

        jsondataasbytes = output.encode('utf-8')  # needs to be bytes
        req.add_header('Content-Length', len(jsondataasbytes))
        req.add_header('TOKEN', self.tokenReSendMessage)

        # resend message to url from configuration
        try:
            response = urllib.request.urlopen(req, jsondataasbytes)
            self.output(response.info())
        except Exception as e:
            self.output(e)

        self.output(output, tag=None, prompt=not self.sendReceipts)

        if self.sendReceipts:
            self.toLower(message.ack(self.sendRead))
            self.output("Sent delivered receipt" + " and Read" if self.sendRead else "",
                        tag="Message %s" % message.getId())

    @EventCallback(EVENT_SEND_MESSAGE)
    def doSendMesage(self, layerEvent):
        content = layerEvent.getArg("msg")
        number = layerEvent.getArg("number")
        
        jid = number

        if self.assertConnected():
            self.send_message(content,number)
            self.output("Send Message to %s : %s" % (number, content))
        else:
            reconnect = False
            reconnect = self.reconnecting()

            if(reconnect):
                self.send_message(content,number)
                self.output("Send Message to %s : %s" % (number, content))

    def send_message(self,content,number):
        outgoingMessage = TextMessageProtocolEntity(
        content.encode("utf-8") if sys.version_info >= (3, 0) else content, to=self.aliasToJid(number))

        self.toLower(outgoingMessage)

    def reconnecting(self):
        attempts = 0
        while (attempts < RECONNECT_ATTEMPTS or RECONNECT_ATTEMPTS == -1) and not self.connected:
            attempts += 1
            self.output('Reconnecting... Attempt {}'.format(attempts))
            self.connect()
            sleep(RECONNECT_TIMEOUT)
        return self.connected

    def getTextMessageBody(self, message):
        return message.getBody()

    def getMediaMessageBody(self, message):
        if message.getMediaSize()==0:
            return "[Media Type: unhandled]"
        elif message.getMediaType() in ("image", "audio", "video"):
            return self.getDownloadableMediaMessageBody(message)
        else:
            return "[Media Type: %s]" % message.getMediaType()

    def getDownloadableMediaMessageBody(self, message):
        return "{{\"type\":\"{media_type}\",\"size\":\"{media_size}\",\"url\":\"{media_url}\",\"content\":\"{media_content}\",\"caption\":\"{media_caption}\"}}".format(
            media_type=message.getMediaType(),
            media_size=message.getMediaSize(),
            media_url=message.getMediaUrl(),
	        media_content=base64.b64encode(message.getMediaContent()).decode(),
            media_caption=message.getCaption()
        )

    def getLocationMessageBody(self, message):
        return "{{\"type\":\"{media_type}\",\"latitude\":\"{latitude}\",\"longitude\":\"{longitude}\",\"url\":\"{url}\",\"name\":\"{name}\"}}".format(
            media_type=message.getMediaType(),
            latitude=message.getLatitude(),
            longitude=message.getLongitude(),
            name=message.getLocationName(),
            url=message.getLocationURL()
        )        
        
    def getVCardMessageBody(self, message):
        return "{{\"type\":\"{media_type}\",\"name\":\"{name}\",\"card_data\":\"{card_data}\"}}".format(
            media_type=message.getMediaType(),
            name=message.getName(),
            card_data=message.getCardData().replace('"', '\\"').replace('\n', '\\n'),
        )

    def doSendMedia(self, mediaType, filePath, url, to, ip = None, caption = None):
        if mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE:
            entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption = caption)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO:
            entity = AudioDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_VIDEO:
            entity = VideoDownloadableMediaMessageProtocolEntity.fromFilePath(filePath, url, ip, to, caption = caption)
        self.toLower(entity)

    @EventCallback(EVENT_SEND_VIDEO)
    def video_send(self, layerEvent):
        number = layerEvent.getArg("number")
        path = layerEvent.getArg("path")
        caption = layerEvent.getArg("caption")
        self.output("Send Message to %s : %s" % (number, path))
        self.media_send(number, path, RequestUploadIqProtocolEntity.MEDIA_TYPE_VIDEO,caption)

    @EventCallback(EVENT_SEND_IMAGE)
    def image_send(self, layerEvent):
        number = layerEvent.getArg("number")
        path = layerEvent.getArg("path")
        caption = layerEvent.getArg("caption")
        self.output("Send Message to %s : %s" % (number, path))
        self.media_send(number, path, RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE, caption)

    @EventCallback(EVENT_SEND_AUDIO)
    def audio_send(self, number, path):
        self.media_send(number, path, RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO)


    def media_send(self, number, path, mediaType, caption=None):
        if self.assertConnected():
            jid = self.aliasToJid(number)
            entity = RequestUploadIqProtocolEntity(mediaType, filePath=path)
            successFn = lambda successEntity, originalEntity: self.onRequestUploadResult(jid, mediaType, path,
                                                                                         successEntity, originalEntity,
                                                                                         caption)
            errorFn = lambda errorEntity, originalEntity: self.onRequestUploadError(jid, path, errorEntity,
                                                                                    originalEntity)
            self._sendIq(entity, successFn, errorFn)


    ########### callbacks ############

    def onRequestUploadResult(self, jid, mediaType, filePath, resultRequestUploadIqProtocolEntity, requestUploadIqProtocolEntity, caption = None):

        if resultRequestUploadIqProtocolEntity.isDuplicate():
            self.doSendMedia(mediaType, filePath, resultRequestUploadIqProtocolEntity.getUrl(), jid,
                             resultRequestUploadIqProtocolEntity.getIp(), caption)
        else:
            successFn = lambda filePath, jid, url: self.doSendMedia(mediaType, filePath, url, jid, resultRequestUploadIqProtocolEntity.getIp(), caption)
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
        #resultGetPictureIqProtocolEntiy.writeToFile("/tmp/yowpics/%s_%s.jpg" % (getPictureIqProtocolEntity.getTo(), "preview" if resultGetPictureIqProtocolEntiy.isPreview() else "full"))
        pass

    def __str__(self):
        return "Send Recive Interface Layer"

    def output(self, str, tag="", prompt=""):
        logging.info(str)
        pass