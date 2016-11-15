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

        self.client = Client()

        Sockets.set_ip("")  # TODO set based on cli arg
        self.client.reconnect()
        SocketHandlers.create()

    def run(self):
        Controller.check_input()
        self.client.update()


frontend = Frontend()

while True:
    try:
        frontend.run()
    except KeyboardInterrupt:
        sys.exit()
