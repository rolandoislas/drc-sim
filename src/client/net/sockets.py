import socket

import time

from src.common.data import constants
from src.common.net.codec import Codec


class Sockets:

    def __init__(self):
        self.SERVER_IP = ""
        self.VID_S = None
        self.AUD_S = None
        self.CMD_S = None

    @staticmethod
    def client_tcp(ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect((ip, port))
        return sock

    @staticmethod
    def client_udp():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", 0))
        return sock

    def connect(self):
        try:
            self.CMD_S = self.client_udp()
            self.send_command(constants.COMMAND_REGISTER)
            self.VID_S = self.client_tcp(self.SERVER_IP, constants.PORT_SERVER_VID)
            self.AUD_S = self.client_tcp(self.SERVER_IP, constants.PORT_SERVER_AUD)
        except socket.error, e:
            raise e

    def set_ip(self, ip):
        self.SERVER_IP = ip

    def send_command(self, name, data=""):
        self.CMD_S.sendto(Codec.encode_command(name, data), (self.SERVER_IP, constants.PORT_SERVER_CMD))

Sockets = Sockets()
