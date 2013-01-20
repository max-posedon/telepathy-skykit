from dbus.types import String, UInt32

from telepathy.constants import (
    CONNECTION_PRESENCE_STATUS_AVAILABLE,
    CONNECTION_PRESENCE_STATUS_OFFLINE,
    CONNECTION_PRESENCE_TYPE_AVAILABLE,
    CONNECTION_PRESENCE_TYPE_OFFLINE,
    HANDLE_TYPE_CONTACT,
)
from telepathy.interfaces import (
    CHANNEL,
    CHANNEL_TYPE_TEXT,
    CONNECTION_INTERFACE_ALIASING,
    CONNECTION_INTERFACE_CONTACT_GROUPS,
    CONNECTION_INTERFACE_CONTACT_LIST,
    CONNECTION_INTERFACE_CONTACTS,
    CONNECTION_INTERFACE_REQUESTS,
    CONNECTION_INTERFACE_SIMPLE_PRESENCE,
)
from telepathy.server import Protocol, ProtocolInterfacePresence

from skykit import PROTOCOL
from skykit.connection import SkykitConnection


__all__ = (
    'SkykitProtocol',
)


class SkykitProtocol(Protocol, ProtocolInterfacePresence):
    
    _proto = PROTOCOL
    _english_name = PROTOCOL.capitalize()
    _icon = "im-%s" % PROTOCOL
    _vcard_field = "im-%s" % PROTOCOL

    _mandatory_parameters = {
        'account': 's',
        'password': 's',
    }

    _secret_parameters = set([
        'password',
        ])

    _requestable_channel_classes = [
        (
            {
                CHANNEL + '.ChannelType': String(CHANNEL_TYPE_TEXT),
                CHANNEL + '.TargetHandleType': UInt32(HANDLE_TYPE_CONTACT),
            },
            [
                CHANNEL + '.TargetHandle',
                CHANNEL + '.TargetID',
            ]
        ),
    ]

    _supported_interfaces = [
        CONNECTION_INTERFACE_ALIASING,
        CONNECTION_INTERFACE_CONTACT_GROUPS,
        CONNECTION_INTERFACE_CONTACT_LIST,
        CONNECTION_INTERFACE_CONTACTS,
        CONNECTION_INTERFACE_REQUESTS,
        CONNECTION_INTERFACE_SIMPLE_PRESENCE,
    ]

    _statuses = {
        CONNECTION_PRESENCE_STATUS_AVAILABLE: (
            CONNECTION_PRESENCE_TYPE_AVAILABLE,
            True,
            True,
        ),
        CONNECTION_PRESENCE_STATUS_OFFLINE: (
            CONNECTION_PRESENCE_TYPE_OFFLINE,
            True,
            False,
        ),
    }

    def __init__(self, connection_manager):
        Protocol.__init__(self, connection_manager, PROTOCOL)
        ProtocolInterfacePresence.__init__(self)

    def create_connection(self, connection_manager, parameters):
        return SkykitConnection(self, connection_manager, parameters)
