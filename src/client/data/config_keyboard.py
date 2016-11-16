import pygame

from src.common.data.config import Config


class ConfigKeyboard:
    button_r3 = None
    button_l3 = None
    button_down = None
    button_up = None
    button_left = None
    button_right = None
    button_zr = None
    button_zl = None
    button_home = None
    button_plus = None
    button_minus = None
    button_r = None
    button_l = None
    button_y = None
    button_x = None
    button_b = None
    button_a = None
    config = Config()

    def __init__(self):
        pass

    @classmethod
    def load(cls):
        cls.config.load("~/.drc-sim/keyboard.conf")
        cls.button_a = cls.config.get_int("KEY", "a", None, None, pygame.K_SPACE)
        cls.button_b = cls.config.get_int("KEY", "b", None, None, pygame.K_e)
        cls.button_x = cls.config.get_int("KEY", "x", None, None, pygame.K_d)
        cls.button_y = cls.config.get_int("KEY", "y", None, None, pygame.K_f)
        cls.button_l = cls.config.get_int("KEY", "l", None, None, pygame.K_q, "Left trigger")
        cls.button_r = cls.config.get_int("KEY", "r", None, None, pygame.K_r, "Right Trigger")
        cls.button_zl = cls.config.get_int("KEY", "zl", None, None, pygame.K_1, "Second left trigger")
        cls.button_zr = cls.config.get_int("KEY", "zr", None, None, pygame.K_4, "Second right trigger")
        cls.button_minus = cls.config.get_int("KEY", "minus", None, None, pygame.K_x)
        cls.button_plus = cls.config.get_int("KEY", "plus", None, None, pygame.K_c)
        cls.button_home = cls.config.get_int("KEY", "home", None, None, pygame.K_z)
        cls.button_left = cls.config.get_int("KEY", "left", None, None, pygame.K_LEFT, "D-pad left")
        cls.button_right = cls.config.get_int("KEY", "right", None, None, pygame.K_RIGHT, "D-pad right")
        cls.button_up = cls.config.get_int("KEY", "up", None, None, pygame.K_UP, "D-pad up")
        cls.button_down = cls.config.get_int("KEY", "down", None, None, pygame.K_DOWN, "D-pad down")
        cls.button_l3 = cls.config.get_int("KEY", "l3", None, None, pygame.K_t, "Left joystick pressed")
        cls.button_r3 = cls.config.get_int("KEY", "r3", None, None, pygame.K_g, "Right joystick pressed")

    @classmethod
    def save(cls):
        cls.config.save()
