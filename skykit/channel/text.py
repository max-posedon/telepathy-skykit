import gobject
import re

from dbus.types import Array, Dictionary, String, UInt32, UInt64

from telepathy.constants import CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, HANDLE_TYPE_CONTACT
from telepathy.server import ChannelTypeText, ChannelInterfaceMessages


__all__ = (
    'SkykitTextChannel',
)


class SkykitTextChannel(ChannelTypeText, ChannelInterfaceMessages):
    _supported_content_types = ['text/plain']

    def __init__(self, conn, manager, props, object_path=None):
        _, surpress_handler, handle = manager._get_type_requested_handle(props)
        self.handle = handle
        self.__message_received_id = 0

        ChannelTypeText.__init__(self, conn, manager, props, object_path)
        ChannelInterfaceMessages.__init__(self)
        self._skype_conversation = self._conn._skype.GetConversationByParticipants([handle.get_name()], True, True)

    def SendMessage(self, message, flags):
        skype_message = self._skype_conversation.PostText(message[1]['content'])
        print "D [%s]" % self._skype_conversation.identity, skype_message.guid.encode('hex'), skype_message.author, skype_message.timestamp, skype_message.body_xml
        return skype_message.guid.encode('hex')

    def _message_sent(self, skype_message):
        headers = Dictionary({
            String('message-sent'): UInt64(skype_message.timestamp),
            String('message-token'): String(skype_message.guid.encode('hex')),
            String('message-type'): UInt32(CHANNEL_TEXT_MESSAGE_TYPE_NORMAL),
        }, signature='sv')
        body = Dictionary({
            String('content-type'): String('text/plain'),
            String('content'): self.to_text(skype_message.body_xml),
        }, signature='sv')
        message = Array([headers, body], signature='a{sv}')
        self.MessageSent(message, 0, String(skype_message.guid.encode('hex')))

    def OnMessage(self, skype_message):
        print "E [%s]" % self._skype_conversation.identity, skype_message.guid.encode('hex'), skype_message.author, skype_message.timestamp, skype_message.body_xml
        if skype_message.author == self._conn._skype_account.skypename:
            gobject.timeout_add(0, self._message_sent, skype_message)
        else:
            gobject.timeout_add(0, self._message_received, skype_message)

    def _message_received(self, skype_message):
        self.__message_received_id += 1
        sender = self._conn.ensure_handle(HANDLE_TYPE_CONTACT, skype_message.author)
        header = Dictionary({
            'pending-message-id': UInt32(self.__message_received_id),
            'message-received': UInt64(skype_message.timestamp),
            'message-type': UInt32(CHANNEL_TEXT_MESSAGE_TYPE_NORMAL),
            'message-token': String(skype_message.guid.encode('hex')),
            'message-sender': UInt32(sender),
            'sender-nickname': String(skype_message.author),
            }, signature='sv')
        body = Dictionary({
            String('content-type'): String('text/plain'),
            String('content'): String(self.to_text(skype_message.body_xml)),
        }, signature='sv')
        message = Array([header, body], signature='a{sv}')
        self.MessageReceived(message)

    def to_text(self, s_xml):
        s_xml = re.sub('<a href="(.*)">(.*)</a>', r'\1', s_xml)
        return s_xml
