import sys
import weakref
import gobject

from telepathy import (
    CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATUS_CONNECTING,
    CONNECTION_STATUS_DISCONNECTED,
    CONNECTION_STATUS_REASON_REQUESTED,
    CONNECTION_STATUS_REASON_NONE_SPECIFIED,
    HANDLE_TYPE_CONTACT,
    )
from telepathy.server import Connection, ConnectionInterfaceRequests

from skykit import PROGRAM, PROTOCOL, SKYPEKITROOT, SKYPEKITKEY
sys.path.append(SKYPEKITROOT + '/ipc/python');
sys.path.append(SKYPEKITROOT + '/interfaces/skype/python');

import Skype

__all__ = (
    'SkykitConnection',
)

MySkype = Skype.GetSkype(SKYPEKITKEY)
MySkype.Start()


class SkykitConnection(Connection):

    def __init__(self, protocol, manager, parameters):
        protocol.check_parameters(parameters)
        account = unicode(parameters['account'])

        self._manager = weakref.proxy(manager)
        self._account = (
            parameters['account'].encode('utf-8'),
            parameters['password'].encode('utf-8'),
        )
        Connection.__init__(self, PROTOCOL, account, PROGRAM, protocol)

        self_handle = self.create_handle(HANDLE_TYPE_CONTACT, self._account[0])
        self.set_self_handle(self_handle)

        self.__disconnect_reason = CONNECTION_STATUS_REASON_NONE_SPECIFIED
        print 3, self, protocol, manager, parameters

    def Connect(self):
        print 4, self, self._status, CONNECTION_STATUS_CONNECTED
        if self._status == CONNECTION_STATUS_DISCONNECTED:
            Skype.Account.OnPropertyChange = self.OnPropertyChange
            self._skype_account = MySkype.GetAccount(self._account[0].decode('utf-8'))
            self._skype_account.LoginWithPassword(self._account[1].decode('utf-8'), False, False)
            self._sleep()

    def OnPropertyChange(self, property_name):
        print 11, self, property_name, self._skype_account.status
        if self._skype_account.status == 'LOGGED_IN':
            self._connected()

    def _connected(self):
        print 8, self, self._status, CONNECTION_STATUS_CONNECTED
        self.StatusChanged(CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_REASON_REQUESTED)
        gobject.timeout_add(50, self._check)

    def _sleep(self):
        gobject.timeout_add(100, self._sleep)
        from time import sleep
        sleep(0.1)

    def _check(self):
        print 9, self, self._status, CONNECTION_STATUS_CONNECTED

    def Disconnect(self):
        print 5, self


