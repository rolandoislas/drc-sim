import pygame
import sys

from src.client.client import Client
from src.client.control.controller import Controller
from src.client.control.keyboard import Keyboard
from src.client.net.socket_handlers import SocketHandlers
from src.client.net.sockets import Sockets


class Frontend:
    def __init__(self):
        Controller.set_handler(Keyboard())  # TODO set based on cli arg

        self.video = Client()

        Sockets.set_ip("")  # TODO set based on cli arg
        Sockets.connect()
        SocketHandlers.create()

    @staticmethod
    def check_quit():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

    def run(self):
        self.check_quit()
        Controller.check_input()
        self.video.update()


frontend = Frontend()

while True:
    try:
        frontend.run()
    except KeyboardInterrupt:
        sys.exit()
