import pygame
import select
import socket

from src.client.net.socket_handlers import SocketHandlers
from src.client.net.sockets import Sockets
from src.common.data import constants
from src.common.net.codec import Codec
from src.common.net.net_util import NetUtil


class Client:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((constants.WII_VIDEO_WIDTH, constants.WII_VIDEO_HEIGHT))
        pygame.display.set_caption("drc-sim")

    def update(self):
        self.check_sockets()

    def reconnect(self):
        font = pygame.font.Font(None, 100)
        text = "Reconnecting"
        font.size(text)
        font_surface = font.render(text, 0, (255, 255, 255), (0, 0, 0))
        self.screen.blit(font_surface, (50, 50))
        pygame.display.flip()
        Sockets.connect()

    @staticmethod
    def handle_media_packet(sock):
        data = NetUtil.recv(sock)
        try:
            SocketHandlers.media_handlers[sock].update(data)
        except socket.error:
            print e.strerror

    def check_sockets(self):
        rlist, wlist, xlist = select.select(SocketHandlers.media_handlers.keys() +
                                            SocketHandlers.command_handlers.keys(),
                                            (), (), 1)
        if rlist:
            for sock in rlist:
                # Media incoming socket
                if sock in SocketHandlers.media_handlers.keys():
                    self.handle_media_packet(sock)
                # Command socket
                if sock in SocketHandlers.command_handlers.keys():
                    self.handle_command_packet(sock)

    @staticmethod
    def handle_command_packet(sock):
        data = sock.recv(2048)
        data = Codec.decode_command(data)
        try:
            SocketHandlers.command_handlers[sock].update(data)
        except socket.error, e:
            print e.strerror
