from net import sockets
from net import wii_service, server_service


class SocketHandlers:
    def __init__(self):
        self.service_handlers = None
        self.server_handlers = None

    def create(self):
        self.service_handlers = {
            sockets.Sockets.WII_MSG_S: wii_service.ServiceMSG(),
            sockets.Sockets.WII_VID_S: wii_service.ServiceVSTRM(),
            sockets.Sockets.WII_AUD_S: wii_service.ServiceASTRM(),
            sockets.Sockets.WII_CMD_S: wii_service.ServiceCMD()
        }
        self.server_handlers = {
            sockets.Sockets.SERVER_VID_S: server_service.ServiceVID(),
            sockets.Sockets.SERVER_AUD_S: server_service.ServiceAUD(),
            sockets.Sockets.SERVER_CMD_S: server_service.ServiceCMD
        }
SocketHandlers = SocketHandlers()
