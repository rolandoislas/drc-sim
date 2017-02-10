import select
import socket

import time

from src.server.data.args import Args
from src.server.control.server import Server
from src.server.control.util.controller import Controller
from src.server.data.config import ConfigServer
from src.server.net import socket_handlers
from src.server.net import sockets


class Gamepad:
    def __init__(self):
        self.server = Server()
        sockets.Sockets.connect()
        socket_handlers.SocketHandlers.create()
        ConfigServer.load()
        ConfigServer.save()
        Args.parse_args()
        self.print_init()
        self.has_received_packet = False
        self.wii_packet_time = time.time()

    @staticmethod
    def print_init():
        print "Started drc-sim-backend"
        if Args.args.debug:
            print "Debug logging enabled"
        print "Waiting for Wii U packets"

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
            # Notify once first packet is received
            if not self.has_received_packet:
                self.has_received_packet = True
                print "Received Wii U packet"
            # Update last packet time
            if Args.args.debug:
                self.wii_packet_time = time.time()
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
        self.check_last_packet_time()
        self.handle_sockets()
        Controller.update()

    @staticmethod
    def close():
        for s in socket_handlers.SocketHandlers.wii_handlers.itervalues():
            s.close()

    def check_last_packet_time(self):
        if Args.args.debug and time.time() - self.wii_packet_time >= 10:
            self.wii_packet_time = time.time()
            print "No Wii U packets received in the last 10 seconds"
