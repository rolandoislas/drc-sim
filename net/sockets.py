import socket

from data import constants


class Sockets:

    def __init__(self):
        self.WII_MSG_S = None
        self.WII_VID_S = None
        self.WII_AUD_S = None
        self.WII_HID_S = None
        self.WII_CMD_S = None
        self.SERVER_VID_S = None
        self.SERVER_AUD_S = None
        self.SERVER_CMD_S = None
        self.client_sockets = {}

    @staticmethod
    def service_addend(ip):
        if int(ip.split('.')[3]) == 10:
            return 0
        else:
            return 100

    def udp_service(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, port + self.service_addend(ip)))
        return sock

    # hack for now, replace with dhcp result
    WII_LOCAL_IP = '192.168.1.11'
    SERVER_IP = ''

    @staticmethod
    def server(ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(5)
        return sock

    def connect(self):
        self.WII_MSG_S = self.udp_service(self.WII_LOCAL_IP, constants.WII_PORT_MSG)
        self.WII_VID_S = self.udp_service(self.WII_LOCAL_IP, constants.WII_PORT_VID)
        self.WII_AUD_S = self.udp_service(self.WII_LOCAL_IP, constants.WII_PORT_AUD)
        self.WII_HID_S = self.udp_service(self.WII_LOCAL_IP, constants.WII_PORT_HID)
        self.WII_CMD_S = self.udp_service(self.WII_LOCAL_IP, constants.WII_PORT_CMD)
        self.SERVER_VID_S = self.server(self.SERVER_IP, constants.SERVER_PORT_VID)
        self.SERVER_AUD_S = self.server(self.SERVER_IP, constants.SERVER_PORT_AUD)
        self.SERVER_CMD_S = self.server(self.SERVER_IP, constants.SERVER_PORT_CMD)

Sockets = Sockets()
