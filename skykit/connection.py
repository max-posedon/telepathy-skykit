from time import sleep
import gobject
from dbus.types import Dictionary
import sys
import weakref

from telepathy.constants import (
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
    CONNECTION,
    CONNECTION_INTERFACE_CONTACT_LIST,
)
from telepathy.server import (
    Connection,
    ConnectionInterfaceRequests,
    ConnectionInterfaceContacts,
    ConnectionInterfaceContactList,
)

from skykit import PROGRAM, PROTOCOL, SKYPEKITROOT, SKYPEKITKEY
sys.path.append(SKYPEKITROOT + '/ipc/python');
sys.path.append(SKYPEKITROOT + '/interfaces/skype/python');

import Skype

from skykit.channel_manager import SkykitChannelManager

__all__ = (
    'SkykitConnection',
)

MySkype = Skype.GetSkype(SKYPEKITKEY)
MySkype.Start()

class SkykitConnection(Connection,
    ConnectionInterfaceContactList,
    ConnectionInterfaceContacts,
    ConnectionInterfaceRequests,
    ):

    def __init__(self, protocol, manager, parameters):
        protocol.check_parameters(parameters)
        self._manager = weakref.proxy(manager)

        account = unicode(parameters['account'])
        self._channel_manager = SkykitChannelManager(self, protocol)

        self._account = (
            parameters['account'].encode('utf-8'),
            parameters['password'].encode('utf-8'),
        )
        Connection.__init__(self, PROTOCOL, account, PROGRAM, protocol)
        ConnectionInterfaceContactList.__init__(self)
        ConnectionInterfaceContacts.__init__(self)
        ConnectionInterfaceRequests.__init__(self)

        self_handle = self.ensure_handle(HANDLE_TYPE_CONTACT, self._account[0])
        self.set_self_handle(self_handle)

        self._skype_account = MySkype.GetAccount(self._account[0].decode('utf-8'))
        Skype.Account.OnPropertyChange = self.OnPropertyChange
        Skype.Contact.OnPropertyChange = self.ContactOnPropertyChange

        self.__disconnect_reason = CONNECTION_STATUS_REASON_NONE_SPECIFIED
        self._sleep()

    def _sleep(self):
        sleep(0.1)
        gobject.timeout_add(100, self._sleep)

    def handle(self, handle_type, handle_id):
        self.check_handle(handle_type, handle_id)
        return self._handles[handle_type, handle_id]

    def Connect(self):
        if self._status == CONNECTION_STATUS_DISCONNECTED:
            self._skype_account.LoginWithPassword(self._account[1].decode('utf-8'), False, False)
            self.StatusChanged(CONNECTION_STATUS_CONNECTING, CONNECTION_STATUS_REASON_REQUESTED)

    def _connected(self):
        self.StatusChanged(CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_REASON_REQUESTED)
        self.ContactListStateChanged(CONTACT_LIST_STATE_SUCCESS)

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

    def _disconnected(self):
        self.StatusChanged(CONNECTION_STATUS_DISCONNECTED, self.__disconnect_reason)
        self._manager.disconnected(self)

    def GetContactListAttributes(self, interfaces, hold):
        ret = Dictionary(signature='ua{sv}')

        skypeContactGroup = MySkype.GetHardwiredContactGroup('ALL_KNOWN_CONTACTS')
        skypeContacts = skypeContactGroup.GetContacts()
        CONTACTS = map(lambda c: c.GetIdentity(), skypeContacts)

        for contact in CONTACTS:
            handle = self.ensure_handle(HANDLE_TYPE_CONTACT, contact)
            ret[int(handle)] = Dictionary(signature='sv')
            ret[int(handle)][CONNECTION + '/contact-id'] = contact
            ret[int(handle)][CONNECTION_INTERFACE_CONTACT_LIST + '/subscribe'] = SUBSCRIPTION_STATE_YES
            ret[int(handle)][CONNECTION_INTERFACE_CONTACT_LIST + '/publish'] = SUBSCRIPTION_STATE_YES
        return ret
