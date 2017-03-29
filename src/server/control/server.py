import socket

from src.server.net.codec import Codec
from src.server.net import socket_handlers
from src.server.net import sockets
from src.server.util.logging.logger_backend import LoggerBackend


class Server:
    def __init__(self):
        pass

    @staticmethod
    def handle_client_command_packet(sock):
        try:
            data, address = sock.recvfrom(2048)
            command, data = Codec.decode_command(data)
            socket_handlers.SocketHandlers.server_command_handlers[sock].update(address, command, data)
        except socket.error, e:
            LoggerBackend.warn(e.strerror)

    @staticmethod
    def add_media_client(sock):
        client, address = sock.accept()
        client.settimeout(1)
        sockets.Sockets.add_client_socket((client, address), socket_handlers.SocketHandlers.server_media_handlers[sock])
