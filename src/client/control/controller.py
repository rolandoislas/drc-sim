import time

from src.client.control.control import Control
from src.client.net.sockets import Sockets
from src.common.data import constants
from src.common.net.codec import Codec


class Controller:
    inputHandler = Control()

    def __init__(self):
        pass

    @classmethod
    def check_input(cls):
        cls.input_time = time.time()
        buttonbytes = cls.inputHandler.get_button_input()
        l3r3bytes = cls.inputHandler.get_l3_r3_input()
        touchCoords = cls.inputHandler.get_touch_input()
        jotstickInput = cls.inputHandler.get_joystick_input(0)
        timestamp = time.time()
        if buttonbytes is not None:
            Sockets.send_command(constants.COMMAND_INPUT_BUTTON, Codec.encode_input(buttonbytes, timestamp))
        if l3r3bytes is not None:
            Sockets.send_command(constants.COMMAND_INPUT_L3R3, Codec.encode_input(l3r3bytes, timestamp))
        if touchCoords is not None:
            Sockets.send_command(constants.COMMAND_INPUT_TOUCH, Codec.encode_input(touchCoords, timestamp))
        if jotstickInput is not None:
            Sockets.send_command(constants.COMMAND_INPUT_JOYSTICK, Codec.encode_input(jotstickInput, timestamp))

    @classmethod
    def set_handler(cls, input_handler):
        cls.inputHandler = input_handler

    @classmethod
    def vibrate(cls):
        cls.inputHandler.vibrate()
