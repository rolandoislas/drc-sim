from src.server.net import sockets
from src.server.net.server.audio import ServiceAUD
from src.server.net.server.command import ServiceCMD
from src.server.net.server.video import ServiceVID
from src.server.net.wii.audio import AudioHandler
from src.server.net.wii.command import CommandHandler
from src.server.net.wii.message import MessageHandler
from src.server.net.wii.video import VideoHandler


class SocketHandlers:
    def __init__(self):
        self.wii_handlers = None
        self.server_media_handlers = None
        self.server_command_handlers = None

    def create(self):
        self.wii_handlers = {
            sockets.Sockets.WII_MSG_S: MessageHandler(),
            sockets.Sockets.WII_VID_S: VideoHandler(),
            sockets.Sockets.WII_AUD_S: AudioHandler(),
            sockets.Sockets.WII_CMD_S: CommandHandler()
        }
        self.server_media_handlers = {
            sockets.Sockets.SERVER_VID_S: ServiceVID(),
            sockets.Sockets.SERVER_AUD_S: ServiceAUD()
        }
        self.server_command_handlers = {
            sockets.Sockets.SERVER_CMD_S: ServiceCMD
        }

    def get_handler_keys(self):
        return list(
            list(self.wii_handlers.keys()) +
            list(self.server_media_handlers.keys()) +
            list(self.server_command_handlers.keys())
        )


SocketHandlers = SocketHandlers()
