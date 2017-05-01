import select
import socket
import time
from threading import Thread

from src.server.control.server import Server
from src.server.control.util.controller import Controller
from src.server.data.args import Args
from src.server.data.config_server import ConfigServer
from src.server.net import socket_handlers
from src.server.net import sockets
from src.server.util.logging.logger_backend import LoggerBackend
from src.server.util.status_sending_thread import StatusSendingThread


class Gamepad(StatusSendingThread):
    NO_PACKETS = "NO_PACKETS"
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    WAITING_FOR_PACKET = "WAITING_FOR_PACKET"
    CRASHED = "CRASHED"

    def __init__(self):
        """
        Backend server handler. Processes packets from the Wii U and servers clients.
        """
        super().__init__()
        self.backend_thread = None
        self.set_status(self.STOPPED)
        self.running = False
        self.wii_packet_time = time.time()
        self.has_received_packet = False
        self.server = Server()

    def start(self):
        """
        Start the main thread
        :return: None
        """
        ConfigServer.load()
        ConfigServer.save()
        self.print_init()
        sockets.Sockets.connect()
        socket_handlers.SocketHandlers.create()
        self.running = True
        LoggerBackend.debug("Starting backend thread")
        self.backend_thread = Thread(target=self.update, name="Backend Thread")
        self.backend_thread.start()
        LoggerBackend.debug("Post backend thread")

    def print_init(self):
        """
        Log the initialization messages
        :return: None
        """
        LoggerBackend.info("Started drc-sim-backend")
        self.print_config()
        LoggerBackend.info("Waiting for Wii U packets")

    @staticmethod
    def handle_wii_packet(sock):
        """
        Receive data from a socket and pass it to the appropriate packet handler.
        :param sock: Wii U datagram Socket
        :return: None
        """
        data = sock.recv(2048)
        # Dump packet
        if Args.args.dump:
            if sock == sockets.Sockets.WII_VID_S:
                with open("video.bin", "ab") as video_packet:
                    video_packet.write(data + b"|\n")
        # Handle packet
        try:
            socket_handlers.SocketHandlers.wii_handlers[sock].update(data)
        except socket.error as e:
            LoggerBackend.warn(str(e) + str(e.errno))

    def handle_sockets(self):
        """
        Check if any sockets have data and pass then to their handler.
        :return: None
        """
        # Group all sockets
        rlist, wlist, xlist = select.select(socket_handlers.SocketHandlers.get_handler_keys(),
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
        """
        Main loop
        :return: None
        """
        while self.running:
            try:
                self.check_last_packet_time()
                self.handle_sockets()
                Controller.update()
            except Exception as e:
                self.set_status(self.CRASHED)
                LoggerBackend.throw(e)

    def close(self):
        """
        Stop the backend thread
        :return: None
        """
        if not self.running:
            LoggerBackend.debug("Ignored stop request: already stopped")
            return
        LoggerBackend.debug("Stopping backend")
        self.running = False
        try:
            self.backend_thread.join()
        except RuntimeError as e:
            LoggerBackend.exception(e)
        LoggerBackend.debug("Closing handlers")
        if socket_handlers.SocketHandlers.wii_handlers:
            for s in socket_handlers.SocketHandlers.wii_handlers.values():
                s.close()
        LoggerBackend.debug("Closing sockets")
        sockets.Sockets.close()
        self.clear_status_change_listeners()
        LoggerBackend.debug("Backend closed")

    def check_last_packet_time(self):
        """
        Checks if the server should shutdown after not receiving  packets for more than a minute
        :return: None
        """
        if not self.has_received_packet:
            status = self.WAITING_FOR_PACKET
        elif time.time() - self.wii_packet_time >= 60:
            status = Gamepad.NO_PACKETS
        else:
            status = Gamepad.RUNNING
        self.set_status(status)

    @staticmethod
    def print_config():
        """
        Logs the server configuration info
        :return: None
        """
        LoggerBackend.info("Config: FPS %d", ConfigServer.fps)
        LoggerBackend.info("Config: Input Delay %f", ConfigServer.input_delay)
        LoggerBackend.info("Config: Image Quality %d", ConfigServer.quality)
        LoggerBackend.info("Config: Stream Audio %s", ConfigServer.stream_audio)
