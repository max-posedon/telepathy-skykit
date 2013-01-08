from telepathy.server import ConnectionManager

from skykit import PROGRAM, PROTOCOL
from skykit.protocol import SkykitProtocol

__all__ = (
	'SkykitConnectionManager',
)


class SkykitConnectionManager(ConnectionManager):
    def __init__(self, shutdown_func=None):
        ConnectionManager.__init__(self, PROGRAM)
        self._implement_protocol(PROTOCOL, SkykitProtocol)
