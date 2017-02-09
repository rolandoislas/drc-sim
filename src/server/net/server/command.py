import socket

from src.common.data import constants
from src.common.net.codec import Codec
from src.server.control.util.controller import Controller
from src.server.net import sockets


class ServiceCMD:
    __name__ = "ServiceCMD"

    def __init__(self):
        pass

    def update(self, address, command, data):
        if command == constants.COMMAND_REGISTER:
            self.register_client(address)
        elif command == constants.COMMAND_INPUT_BUTTON:
            Controller.set_button_input(data)
        elif command == constants.COMMAND_INPUT_L3R3:
            Controller.set_l3r3_input(data)
        elif command == constants.COMMAND_INPUT_TOUCH:
            Controller.set_touch_input(data)
        elif command == constants.COMMAND_INPUT_JOYSTICK:
            Controller.set_joystick_input(data)

    @staticmethod
    def register_client(address):
        sockets.Sockets.add_client_socket(address, ServiceCMD)

    @classmethod
    def broadcast(cls, command, data=""):
        for address in sockets.Sockets.client_sockets.keys():
            if sockets.Sockets.client_sockets[address].__name__ == ServiceCMD.__name__:
                try:
                    sockets.Sockets.SERVER_CMD_S.sendto(Codec.encode_command(command, data), address)
                except socket.error:
                    sockets.Sockets.remove_client_socket(address)


ServiceCMD = ServiceCMD()
