from time import sleep
import gobject
from dbus.types import Array, Dictionary, String, Struct, UInt32
import sys
import weakref

from telepathy.constants import (
    CONNECTION_PRESENCE_TYPE_AVAILABLE,
    CONNECTION_PRESENCE_STATUS_AVAILABLE,
    CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATUS_CONNECTING,
    CONNECTION_STATUS_DISCONNECTED,
    CONNECTION_STATUS_REASON_REQUESTED,
    CONNECTION_STATUS_REASON_NONE_SPECIFIED,
    CONTACT_LIST_STATE_SUCCESS,
    HANDLE_TYPE_CONTACT,
    SUBSCRIPTION_STATE_YES,
)
from telepathy.interfaces import (
    CHANNEL,
    CHANNEL_TYPE_TEXT,
    CONNECTION,
    CONNECTION_INTERFACE_ALIASING,
    CONNECTION_INTERFACE_AVATARS,
    CONNECTION_INTERFACE_CONTACT_GROUPS,
    CONNECTION_INTERFACE_CONTACT_LIST,
    CONNECTION_INTERFACE_SIMPLE_PRESENCE,
)
from telepathy.server import (
    Connection,
    ConnectionInterfaceAliasing,
    ConnectionInterfaceAvatars,
    ConnectionInterfaceContacts,
    ConnectionInterfaceContactGroups,
    ConnectionInterfaceContactList,
    ConnectionInterfaceRequests,
    ConnectionInterfaceSimplePresence,
)

from skykit import PROGRAM, PROTOCOL, SKYPEKITROOT, SKYPEKITKEY, GROUP, AVATAR_MIME
sys.path.append(SKYPEKITROOT + '/ipc/python');
sys.path.append(SKYPEKITROOT + '/interfaces/skype/python');

import Skype

from skykit.channel_manager import SkykitChannelManager

__all__ = (
    'SkykitConnection',
)


class SkykitConnection(Connection,
    ConnectionInterfaceAliasing,
    ConnectionInterfaceAvatars,
    ConnectionInterfaceContactGroups,
    ConnectionInterfaceContactList,
    ConnectionInterfaceContacts,
    ConnectionInterfaceRequests,
    ConnectionInterfaceSimplePresence,
    ):

    def __init__(self, protocol, manager, parameters):
        protocol.check_parameters(parameters)
        self._manager = weakref.proxy(manager)

        account = unicode(parameters['account'])
        self._statuses = protocol._statuses
        self._channel_manager = SkykitChannelManager(self, protocol)

        self._account = (
            parameters['account'].encode('utf-8'),
            parameters['password'].encode('utf-8'),
        )
        Connection.__init__(self, PROTOCOL, account, PROGRAM, protocol)
        ConnectionInterfaceAliasing.__init__(self)
        ConnectionInterfaceAvatars.__init__(self)
        ConnectionInterfaceContactGroups.__init__(self)
        ConnectionInterfaceContactList.__init__(self)
        ConnectionInterfaceContacts.__init__(self)
        ConnectionInterfaceRequests.__init__(self)
        ConnectionInterfaceSimplePresence.__init__(self)

        self_handle = self.ensure_handle(HANDLE_TYPE_CONTACT, self._account[0])
        self.set_self_handle(self_handle)

        self._skype = Skype.GetSkype(SKYPEKITKEY)
        self._skype.Start()
        self._skype_account = self._skype.GetAccount(self._account[0].decode('utf-8'))
        Skype.Account.OnPropertyChange = self.OnPropertyChange
        Skype.Contact.OnPropertyChange = self.ContactOnPropertyChange
        Skype.Skype.OnConversationListChange = self.OnConversationListChange
        Skype.Skype.OnMessage = self.OnMessage

        self.__disconnect_reason = CONNECTION_STATUS_REASON_NONE_SPECIFIED

    def _sleep(self):
        if self._status != CONNECTION_STATUS_DISCONNECTED:
            sleep(0.1)
            gobject.timeout_add(100, self._sleep)

    def handle(self, handle_type, handle_id):
        self.check_handle(handle_type, handle_id)
        return self._handles[handle_type, handle_id]

    def Connect(self):
        if self._status == CONNECTION_STATUS_DISCONNECTED:
            self._skype_account.LoginWithPassword(self._account[1].decode('utf-8'), False, False)
            self.StatusChanged(CONNECTION_STATUS_CONNECTING, CONNECTION_STATUS_REASON_REQUESTED)
            self._sleep()

    def _connected(self):
        self._groups = [GROUP]

        self.StatusChanged(CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_REASON_REQUESTED)
        self.ContactListStateChanged(CONTACT_LIST_STATE_SUCCESS)

        convList = self._skype.GetConversationList('INBOX_CONVERSATIONS')
        print map(lambda c: c.identity, convList)

    def Disconnect(self):
        self.__disconnect_reason = CONNECTION_STATUS_REASON_REQUESTED
        self._skype_account.Logout(clear_saved_pwd=True)

    def OnPropertyChange(self, property_name):
        print "A", property_name
        if property_name == 'status':
            print ".", self._skype_account.status
            if self._skype_account.status == 'LOGGED_IN':
                self._connected()
            if self._skype_account.status == 'LOGGED_OUT':
                self._disconnected()

    def ContactOnPropertyChange(self, property_name):
        print "B", property_name

    def OnConversationListChange(self, conversation, type_, added):
        print "H", conversation.identity, type_, added

    def _disconnected(self):
        self._groups = []

        self.StatusChanged(CONNECTION_STATUS_DISCONNECTED, self.__disconnect_reason)
        self._manager.disconnected(self)

    def GetContactListAttributes(self, interfaces, hold):
        ret = Dictionary(signature='ua{sv}')

        skypeContactGroup = self._skype.GetHardwiredContactGroup('ALL_KNOWN_CONTACTS')
        skypeContacts = skypeContactGroup.GetContacts()
        CONTACTS = map(lambda c: c.GetIdentity(), skypeContacts)

        for contact in CONTACTS:
            handle = self.ensure_handle(HANDLE_TYPE_CONTACT, contact)
            ret[int(handle)] = Dictionary(signature='sv')
            ret[int(handle)][CONNECTION + '/contact-id'] = contact
            ret[int(handle)][CONNECTION_INTERFACE_AVATARS + '/token'] = contact
            ret[int(handle)][CONNECTION_INTERFACE_ALIASING + '/alias'] = contact
            ret[int(handle)][CONNECTION_INTERFACE_CONTACT_LIST + '/subscribe'] = SUBSCRIPTION_STATE_YES
            ret[int(handle)][CONNECTION_INTERFACE_CONTACT_LIST + '/publish'] = SUBSCRIPTION_STATE_YES
            ret[int(handle)][CONNECTION_INTERFACE_CONTACT_GROUPS + '/groups'] = Array([String(GROUP)], signature='s')
            ret[int(handle)][CONNECTION_INTERFACE_SIMPLE_PRESENCE + '/presence'] = Struct(
                (CONNECTION_PRESENCE_TYPE_AVAILABLE, CONNECTION_PRESENCE_STATUS_AVAILABLE, "avail"),
                signature='uss',
            )
        return ret

    def OnMessage(self, message, changes_inbox_timestamp, supersedes_history_message, conversation):
        print "C [%s]" % conversation.identity, message.author, message.body_xml
        channel = self._start_conversation(conversation)
        gobject.timeout_add(100, channel.OnMessage, message)
        print "."

    def _start_conversation(self, conversation):
        handle = self.ensure_handle(HANDLE_TYPE_CONTACT, conversation.identity)
        props = {
            CHANNEL + '.ChannelType': CHANNEL_TYPE_TEXT,
            CHANNEL + '.TargetHandle': handle.get_id(),
            CHANNEL + '.TargetHandleType': HANDLE_TYPE_CONTACT,
            CHANNEL + '.Requested': False,
        }
        return self._channel_manager.channel_for_props(props, signal=True)

    def GetPresences(self, contacts):
        presences = Dictionary(signature='u(uss)')
        for handle_id in contacts:
            handle = self.handle(HANDLE_TYPE_CONTACT, handle_id)
            presences[handle] = Struct(
                (CONNECTION_PRESENCE_TYPE_AVAILABLE, CONNECTION_PRESENCE_STATUS_AVAILABLE, "avail"),
                signature='uss',
            )
        return presences

    def GetAliases(self, contacts):
        aliases = Dictionary(signature='us')
        for handle_id in contacts:
            handle = self.handle(HANDLE_TYPE_CONTACT, handle_id)
            aliases[handle_id] = String(handle.name)
        return aliases

    def GetKnownAvatarTokens(self, contacts):
        tokens = Dictionary(signature='us')
        for handle_id in contacts:
            handle = self.handle(HANDLE_TYPE_CONTACT, handle_id)
            tokens[handle_id] = String(handle.name)
        return tokens

    def RequestAvatars(self, contacts):
        for handle_id in contacts:
            gobject.timeout_add(0, self._avatar_retrieved, handle_id)

    def _avatar_retrieved(self, handle_id):
        handle = self.handle(HANDLE_TYPE_CONTACT, handle_id)
        skype_contact = self._skype.GetContact(handle.name)
        present, avatar = skype_contact.GetAvatar()
        if present:
            self.AvatarRetrieved(UInt32(handle_id), String(handle.name), avatar, AVATAR_MIME)
