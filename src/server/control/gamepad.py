import logging
import select
import socket
import time

from src.server.control.server import Server
from src.server.control.util.controller import Controller
from src.server.data.args import Args
from src.server.data.config_server import ConfigServer
from src.server.net import socket_handlers
from src.server.net import sockets
from src.server.util.logging.logger_backend import LoggerBackend


class Gamepad:
    def __init__(self):
        Args.parse_args()
        self.set_logging_level()
        ConfigServer.load()
        ConfigServer.save()
        self.print_init()
        self.server = Server()
        sockets.Sockets.connect()
        socket_handlers.SocketHandlers.create()
        self.has_received_packet = False
        self.wii_packet_time = time.time()

    def print_init(self):
        LoggerBackend.info("Started drc-sim-backend")
        LoggerBackend.debug("Debug logging enabled")
        LoggerBackend.extra("Extra debug logging enabled")
        LoggerBackend.finer("Finer debug logging enabled")
        LoggerBackend.verbose("Verbose logging enabled")
        self.print_config()
        LoggerBackend.info("Waiting for Wii U packets")

    @staticmethod
    def handle_wii_packet(sock):
        data = sock.recv(2048)
        try:
            socket_handlers.SocketHandlers.wii_handlers[sock].update(data)
        except socket.error, e:
            LoggerBackend.warn(str(e) + str(e.errno))

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
                LoggerBackend.info("Received Wii U packet")
            # Update last packet time
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
        if time.time() - self.wii_packet_time >= 60:
            LoggerBackend.throw("No Wii U packets received in the last minute. Shutting down.")

    @staticmethod
    def set_logging_level():
        if Args.args.debug:
            LoggerBackend.set_level(logging.DEBUG)
        elif Args.args.extra:
            LoggerBackend.set_level(LoggerBackend.EXTRA)
        elif Args.args.finer:
            LoggerBackend.set_level(LoggerBackend.FINER)
        elif Args.args.verbose:
            LoggerBackend.set_level(LoggerBackend.VERBOSE)
        else:
            LoggerBackend.set_level(logging.INFO)

    @staticmethod
    def print_config():
        LoggerBackend.info("Config: FPS %d", ConfigServer.fps)
        LoggerBackend.info("Config: Input Delay %f", ConfigServer.input_delay)
        LoggerBackend.info("Config: Image Quality %d", ConfigServer.quality)
        LoggerBackend.info("Config: Stream Audio %s", ConfigServer.stream_audio)
