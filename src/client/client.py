import pygame
import select
import socket
import time
import sys

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
        self.check_quit()
        self.check_sockets()

    def reconnect(self):
        # close handlers
        if SocketHandlers.media_handlers:
            for handler in SocketHandlers.media_handlers.values():
                print handler
                handler.close()
        # draw to surface
        font = pygame.font.Font(None, 100)
        text = "Reconnecting"
        font.size(text)
        font_surface = font.render(text, 0, (255, 255, 255), (0, 0, 0))
        self.screen.blit(font_surface, (50, 50))
        pygame.display.flip()
        # Reconnect
        connected = False
        while not connected:
            try:
                Sockets.connect()
                SocketHandlers.create()
                connected = True
            except socket.error:
                start = time.time()
                while time.time() - start < 5:
                    self.check_quit()

    @staticmethod
    def check_quit():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

    @staticmethod
    def handle_media_packet(sock, buffer_id):
        data = NetUtil.recv(sock, buffer_id)
        SocketHandlers.media_handlers[sock].update(data)

    def check_sockets(self):
        rlist, wlist, xlist = select.select(SocketHandlers.media_handlers.keys() +
                                            SocketHandlers.command_handlers.keys(),
                                            (), (), .00001)
        try:
            if rlist:
                for sock in rlist:
                    # Video incoming socket
                    if sock is SocketHandlers.media_handlers.keys()[0]:
                        self.handle_media_packet(sock, "video")
                    # Audio incoming socket
                    if sock is SocketHandlers.media_handlers.keys()[1]:
                        self.handle_media_packet(sock, "audio")
                    # Command socket
                    if sock in SocketHandlers.command_handlers.keys():
                        self.handle_command_packet(sock)
        except socket.error:
            self.reconnect()

    @staticmethod
    def handle_command_packet(sock):
        data = sock.recv(2048)
        command, data = Codec.decode_command(data)
        SocketHandlers.command_handlers[sock].update(command, data)
