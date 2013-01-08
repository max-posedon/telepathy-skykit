from telepathy.server import Protocol

from skykit import PROTOCOL
from skykit.connection import SkykitConnection


__all__ = (
    'SkykitProtocol',
)


class SkykitProtocol(Protocol):
    
    _proto = PROTOCOL
    _english_name = "Skype"
    _icon = "im-skype"
    _vcard_field = "im-skype"

    _mandatory_parameters = {
        'account': 's',
        'password': 's',
    }
    _secret_parameters = set([
        'password',
        ])
    _requestable_channel_classes = [
        ]
    _supported_interfaces = [
        ]

    _statuses = {
    }

    def __init__(self, connection_manager):
        Protocol.__init__(self, connection_manager, PROTOCOL)
        print 1, self, connection_manager

    def create_connection(self, connection_manager, parameters):
        print 0
        conn = SkykitConnection(self, connection_manager, parameters)
        print 2, self, connection_manager, parameters, conn
        return conn
