import pygame

from src.client.control.control import Control
from src.client.data.config_joystick import ConfigJoystick
from src.common.data import buttons


class Joystick(Control):

    def __init__(self):
        Control.__init__(self)
        ConfigJoystick.load()
        ConfigJoystick.save()

    def get_button_input(self):
        joysticks = self.get_joysticks()
        button_bits = 0
        for joystick in joysticks:
            joystick.init()
            # Check Buttons
            if self.is_pressed(joystick, ConfigJoystick.button_a):
                button_bits |= buttons.BUTTON_A
            if self.is_pressed(joystick, ConfigJoystick.button_b):
                button_bits |= buttons.BUTTON_B
            if self.is_pressed(joystick, ConfigJoystick.button_x):
                button_bits |= buttons.BUTTON_X
            if self.is_pressed(joystick, ConfigJoystick.button_y):
                button_bits |= buttons.BUTTON_Y
            if self.is_pressed(joystick, ConfigJoystick.button_l):
                button_bits |= buttons.BUTTON_L
            if self.is_pressed(joystick, ConfigJoystick.button_r):
                button_bits |= buttons.BUTTON_R
            if self.is_pressed(joystick, ConfigJoystick.button_minus):
                button_bits |= buttons.BUTTON_MINUS
            if self.is_pressed(joystick, ConfigJoystick.button_plus):
                button_bits |= buttons.BUTTON_PLUS
            if self.is_pressed(joystick, ConfigJoystick.button_home):
                button_bits |= buttons.BUTTON_HOME
            if self.is_pressed(joystick, ConfigJoystick.button_zl):
                button_bits |= buttons.BUTTON_ZL
            if self.is_pressed(joystick, ConfigJoystick.button_zr):
                button_bits |= buttons.BUTTON_ZR
            # Check Movement - D-pad
            hat = joystick.get_hat(0)
            if hat[0] == 1:
                button_bits |= buttons.BUTTON_RIGHT
            elif hat[0] == -1:
                button_bits |= buttons.BUTTON_LEFT
            if hat[1] == 1:
                button_bits |= buttons.BUTTON_UP
            elif hat[1] == -1:
                button_bits |= buttons.BUTTON_DOWN
            return button_bits if button_bits > 0 else None

    @staticmethod
    def get_joysticks():
        """
        Get avaliable joysticks
        :return: array of joysticks
        """
        pygame.joystick.init()
        return [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

    def get_l3_r3_input(self):
        joysticks = self.get_joysticks()
        button_bits = 0
        for joystick in joysticks:
            joystick.init()
            if self.is_pressed(joystick, ConfigJoystick.button_l3):
                button_bits |= buttons.BUTTON_L3
            if self.is_pressed(joystick, ConfigJoystick.button_r3):
                button_bits |= buttons.BUTTON_R3
        return button_bits

    def get_joystick_input(self, joystick_id):
        joysticks = self.get_joysticks()
        axes = [0, 0, 0, 0]
        for joystick in joysticks:
            joystick.init()
            for axis in range(joystick.get_numaxes()):
                axes[axis] += joystick.get_axis(axis)
        return axes

    @staticmethod
    def is_pressed(joystick, button):
        if button < 0:
            return False
        return joystick.get_button(button)
