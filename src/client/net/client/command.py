from src.client.control.controller import Controller
from src.common.data import constants


class CommandHandler:
    def __init__(self):
        pass

    def update(self, command, data):
        if command == constants.COMMAND_VIBRATE:
            Controller.vibrate()
