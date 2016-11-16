import pygame

from src.client.control.control import Control
from src.client.data.config_keyboard import ConfigKeyboard
from src.common.data import buttons


class Keyboard(Control):

    def __init__(self):
        Control.__init__(self)
        ConfigKeyboard.load()
        ConfigKeyboard.save()

    def get_button_input(self):
        keys = pygame.key.get_pressed()
        button_bits = 0
        # Check buttons
        if keys[ConfigKeyboard.button_a]:
            button_bits |= buttons.BUTTON_A
        if keys[ConfigKeyboard.button_b]:
            button_bits |= buttons.BUTTON_B
        if keys[ConfigKeyboard.button_x]:
            button_bits |= buttons.BUTTON_X
        if keys[ConfigKeyboard.button_y]:
            button_bits |= buttons.BUTTON_Y
        if keys[ConfigKeyboard.button_l]:
            button_bits |= buttons.BUTTON_L
        if keys[ConfigKeyboard.button_r]:
            button_bits |= buttons.BUTTON_R
        if keys[ConfigKeyboard.button_minus]:
            button_bits |= buttons.BUTTON_MINUS
        if keys[ConfigKeyboard.button_plus]:
            button_bits |= buttons.BUTTON_PLUS
        if keys[ConfigKeyboard.button_home]:
            button_bits |= buttons.BUTTON_HOME
        if keys[ConfigKeyboard.button_zl]:
            button_bits |= buttons.BUTTON_ZL
        if keys[ConfigKeyboard.button_zr]:
            button_bits |= buttons.BUTTON_ZR
        # Check Movement
        if keys[ConfigKeyboard.button_right]:
            button_bits |= buttons.BUTTON_RIGHT
        elif keys[ConfigKeyboard.button_left]:
            button_bits |= buttons.BUTTON_LEFT
        if keys[ConfigKeyboard.button_up]:
            button_bits |= buttons.BUTTON_UP
        elif keys[ConfigKeyboard.button_down]:
            button_bits |= buttons.BUTTON_DOWN
        return button_bits if button_bits > 0 else None

    def get_l3_r3_input(self):
        """
        Check if JOYSTICKS are depressed.
        :return: int bits
        """
        keys = pygame.key.get_pressed()
        button_bits = 0
        if keys[ConfigKeyboard.button_l3]:
            button_bits |= buttons.BUTTON_L3
        if keys[ConfigKeyboard.button_r3]:
            button_bits |= buttons.BUTTON_R3
        return button_bits if button_bits > 0 else None

    def get_joystick_input(self, joystick_id):
        return None
        # TODO get origin based on some mouse implementation
        # determine which joystick and direction from id

    def get_touch_input(self):
        if not pygame.mouse.get_pressed()[0]:
            return None
        point = pygame.mouse.get_pos()
        screen = pygame.display.get_surface().get_size()
        return point, screen
