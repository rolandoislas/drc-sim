import sys

from src.client.client import Client
from src.client.control.controller import Controller
from src.client.control.keyboard import Keyboard
from src.client.net.socket_handlers import SocketHandlers
from src.client.net.sockets import Sockets


class Frontend:
    def __init__(self):
        # Check CLI arguments
        ip = sys.argv[1] if len(sys.argv) > 1 else ""

        # Create set controller type
        Controller.set_handler(Keyboard())  # TODO default to touch interface

        # Create client instance
        self.client = Client()

        # Create socks handlers and establish first connection
        Sockets.set_ip(ip)
        self.client.reconnect()
        SocketHandlers.create()

    def run(self):
        # Check and send client input
        Controller.check_input()
        # Check for data from Wii U
        self.client.update()

frontend = Frontend()

while True:
    try:
        frontend.run()
    except KeyboardInterrupt:
        sys.exit()
