import pygame

from control import buttons


def get_input():
    keys = pygame.key.get_pressed()
    button_bits = 0
    # Check buttons
    if keys[pygame.K_SPACE]:
        button_bits |= buttons.BUTTON_A
    if keys[pygame.K_e]:
        button_bits |= buttons.BUTTON_B
    if keys[pygame.K_d]:
        button_bits |= buttons.BUTTON_X
    if keys[pygame.K_f]:
        button_bits |= buttons.BUTTON_Y
    if keys[pygame.K_q]:
        button_bits |= buttons.BUTTON_L
    if keys[pygame.K_r]:
        button_bits |= buttons.BUTTON_R
    if keys[pygame.K_x]:
        button_bits |= buttons.BUTTON_MINUS
    if keys[pygame.K_c]:
        button_bits |= buttons.BUTTON_PLUS
    if keys[pygame.K_z]:
        button_bits |= buttons.BUTTON_HOME
    if keys[pygame.K_1]:
        button_bits |= buttons.BUTTON_ZL
    if keys[pygame.K_4]:
        button_bits |= buttons.BUTTON_ZR
    # Check Movement
    if keys[pygame.K_RIGHT]:
        button_bits |= buttons.HAT_RIGHT
    elif keys[pygame.K_LEFT]:
        button_bits |= buttons.HAT_LEFT
    else:
        button_bits |= buttons.HAT_CENTER
    if keys[pygame.K_UP]:
        button_bits |= buttons.HAT_UP
    elif keys[pygame.K_DOWN]:
        button_bits |= buttons.HAT_DOWN
    else:
        button_bits |= buttons.HAT_CENTER
    return button_bits


def get_l3_r3_input():
    keys = pygame.key.get_pressed()
    button_bits = 0
    if keys[pygame.K_t]:
        button_bits |= buttons.BUTTON_L3
    if keys[pygame.K_g]:
        button_bits |= buttons.BUTTON_R3
    return button_bits
