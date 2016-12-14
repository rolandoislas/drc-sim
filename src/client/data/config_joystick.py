import pygame

from src.client.data.config_keyboard import ConfigKeyboard
from src.common.data.config import Config


class ConfigJoystick(ConfigKeyboard):
    config = Config()

    def __init__(self):
        ConfigKeyboard.__init__(self)

    @classmethod
    def load(cls):
        cls.config.load("~/.drc-sim/joystick.conf")
        cls.button_a = cls.config.get_int("BUTTON", "a", None, None, 1)
        cls.button_b = cls.config.get_int("BUTTON", "b", None, None, 2)
        cls.button_x = cls.config.get_int("BUTTON", "x", None, None, 0)
        cls.button_y = cls.config.get_int("BUTTON", "y", None, None, 3)
        cls.button_l = cls.config.get_int("BUTTON", "l", None, None, 4, "Left trigger")
        cls.button_r = cls.config.get_int("BUTTON", "r", None, None, 5, "Right Trigger")
        cls.button_zl = cls.config.get_int("BUTTON", "zl", None, None, 6, "Second left trigger")
        cls.button_zr = cls.config.get_int("BUTTON", "zr", None, None, 7, "Second right trigger")
        cls.button_minus = cls.config.get_int("BUTTON", "minus", None, None, -1)
        cls.button_plus = cls.config.get_int("BUTTON", "plus", None, None, -1)
        cls.button_home = cls.config.get_int("BUTTON", "home", None, None, 9)
        cls.button_l3 = cls.config.get_int("BUTTON", "l3", None, None, 10, "Left joystick pressed")
        cls.button_r3 = cls.config.get_int("BUTTON", "r3", None, None, 11, "Right joystick pressed")

    @classmethod
    def save(cls):
        cls.config.save()
