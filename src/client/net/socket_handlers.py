from src.client.net.sockets import Sockets
from src.client.net.client.audio import AudioHandler
from src.client.net.client.command import CommandHandler
from src.client.net.client.video import VideoHandler


class SocketHandlers:
    def __init__(self):
        self.media_handlers = None
        self.command_handlers = None

    def create(self):
        self.media_handlers = {
            Sockets.AUD_S: AudioHandler(),
            Sockets.VID_S: VideoHandler()
        }
        self.command_handlers = {
            Sockets.CMD_S: CommandHandler()
        }
SocketHandlers = SocketHandlers()
