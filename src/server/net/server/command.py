from src.server.data import constants
from src.server.control.util.controller import Controller
from src.server.net import sockets
from src.server.net.codec import Codec
from src.server.util.logging.logger_backend import LoggerBackend


class ServiceCMD:
    __name__ = "ServiceCMD"

    def __init__(self):
        pass

    def update(self, address, command, data):
        LoggerBackend.finer("Received command packet of type %s from client %s: %s" % (command, address, data))
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
        elif command == constants.COMMAND_PING:
            sockets.Sockets.SERVER_CMD_S.sendto(Codec.encode_command(constants.COMMAND_PONG), address)

    @staticmethod
    def register_client(address):
        sockets.Sockets.add_client_socket(address, ServiceCMD)

    @classmethod
    def broadcast(cls, command, data=""):
        sockets.Sockets.broadcast_command_packet(command, data, ServiceCMD.__name__)


ServiceCMD = ServiceCMD()
