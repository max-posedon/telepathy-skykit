from telepathy.interfaces import CHANNEL_TYPE_TEXT
from telepathy.server import ChannelManager

from skykit.channel.text import SkykitTextChannel


__all__ = (
    'SkykitChannelManager',
)


class SkykitChannelManager(ChannelManager):
    __text_channel_id = 0

    def __init__(self, connection, protocol):
        ChannelManager.__init__(self, connection)
        self.set_requestable_channel_classes(protocol.requestable_channels)
        self.implement_channel_classes(CHANNEL_TYPE_TEXT, self._get_text_channel)

    def _get_text_channel(self, props):
        self.__text_channel_id += 1
        path = "TextChannel%d" % self.__text_channel_id
        return SkykitTextChannel(self._conn, self, props, object_path=path)
