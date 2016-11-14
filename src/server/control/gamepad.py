import array
import select
import socket
import time

from src.common.data import constants
from src.server.control.server import Server
from src.server.control.util.controller import Controller
from src.server.net import socket_handlers
from src.server.net import sockets


class Gamepad:
    def __init__(self):
        self.server = Server()
        sockets.Sockets.connect()
        socket_handlers.SocketHandlers.create()

    @staticmethod
    def handle_wii_packet(sock):
        data = sock.recv(2048)
        try:
            socket_handlers.SocketHandlers.wii_handlers[sock].update(data)
        except socket.error, e:
            print str(e) + str(e.errno)

    def handle_sockets(self):
        # Group all sockets
        rlist, wlist, xlist = select.select(socket_handlers.SocketHandlers.wii_handlers.keys() +
                                            socket_handlers.SocketHandlers.server_media_handlers.keys() +
                                            socket_handlers.SocketHandlers.server_command_handlers.keys(),
                                            (), (), 0.001)
        if rlist:
            for sock in rlist:
                # Wii socket
                if sock in socket_handlers.SocketHandlers.wii_handlers.keys():
                    self.handle_wii_packet(sock)
                # Server media socket
                if sock in socket_handlers.SocketHandlers.server_media_handlers.keys():
                    self.server.add_media_client(sock)
                # Command socket
                if sock in socket_handlers.SocketHandlers.server_command_handlers.keys():
                    self.server.handle_client_command_packet(sock)

    def update(self):
        self.handle_sockets()
        Controller.update()

    @staticmethod
    def close():
        for s in socket_handlers.SocketHandlers.wii_handlers.itervalues():
            s.close()
