import select
import socket
import time
from threading import Thread

from src.server.control.server import Server
from src.server.control.util.controller import Controller
from src.server.data.config_server import ConfigServer
from src.server.net import socket_handlers
from src.server.net import sockets
from src.server.util.logging.logger_backend import LoggerBackend


class Gamepad:
    NO_PACKETS = "NO_PACKETS"
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    WAITING_FOR_PACKET = "WAITING_FOR_PACKET"

    def __init__(self):
        self.backend_thread = None
        self.status = self.STOPPED
        self.status_change_listeners = []
        self.running = False
        self.wii_packet_time = time.time()
        self.has_received_packet = False
        self.server = Server()

    def start(self):
        ConfigServer.load()
        ConfigServer.save()
        self.print_init()
        sockets.Sockets.connect()
        socket_handlers.SocketHandlers.create()
        self.running = True
        LoggerBackend.debug("Starting backend thread")
        self.backend_thread = Thread(target=self.update)
        self.backend_thread.start()
        LoggerBackend.debug("Post backend thread")

    def print_init(self):
        LoggerBackend.info("Started drc-sim-backend")
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
        while self.running:
            try:
                self.check_last_packet_time()
                self.handle_sockets()
                Controller.update()
            except Exception, e:
                LoggerBackend.throw(e)

    def close(self):
        if not self.running:
            LoggerBackend.debug("Ignored stop request: already stopped")
            return
        LoggerBackend.debug("Stopping backend")
        self.running = False
        try:
            self.backend_thread.join()
        except RuntimeError, e:
            LoggerBackend.exception(e)
        LoggerBackend.debug("Closing handlers")
        if socket_handlers.SocketHandlers.wii_handlers:
            for s in socket_handlers.SocketHandlers.wii_handlers.itervalues():
                s.close()
        LoggerBackend.debug("Closing sockets")
        sockets.Sockets.close()
        self.status_change_listeners = []
        LoggerBackend.debug("Backend closed")

    def check_last_packet_time(self):
        if not self.has_received_packet:
            status = self.WAITING_FOR_PACKET
        elif time.time() - self.wii_packet_time >= 60:
            status = Gamepad.NO_PACKETS
        else:
            status = Gamepad.RUNNING
        if self.status != status:
            self.status = status
            for listener in self.status_change_listeners:
                listener(status)

    @staticmethod
    def print_config():
        LoggerBackend.info("Config: FPS %d", ConfigServer.fps)
        LoggerBackend.info("Config: Input Delay %f", ConfigServer.input_delay)
        LoggerBackend.info("Config: Image Quality %d", ConfigServer.quality)
        LoggerBackend.info("Config: Stream Audio %s", ConfigServer.stream_audio)

    def add_status_change_listener(self, callback):
        self.status_change_listeners.append(callback)
