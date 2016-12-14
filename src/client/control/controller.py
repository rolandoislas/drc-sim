import time

from src.client.control.control import Control
from src.client.control.joystick import Joystick
from src.client.control.keyboard import Keyboard
from src.client.net.sockets import Sockets
from src.common.data import constants
from src.common.net.codec import Codec


class Controller:
    inputHandlers = [Keyboard(), Joystick()]

    def __init__(self):
        pass

    @classmethod
    def check_input(cls):
        for inputHandler in cls.inputHandlers:
            buttonbytes = inputHandler.get_button_input()
            l3r3bytes = inputHandler.get_l3_r3_input()
            touchCoords = inputHandler.get_touch_input()
            jotstickInput = inputHandler.get_joystick_input(0)
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
    def vibrate(cls):
        for inputHandler in cls.inputHandlers:
            inputHandler.vibrate()
