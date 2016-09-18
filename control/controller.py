from control import keyboard
from net import server_service


def get_input():
    # TODO detect and send other inputs
    return keyboard.get_input() | server_service.ServiceCMD.get_input()


def get_l3_r3_input():
    return keyboard.get_l3_r3_input() | server_service.ServiceCMD.get_l3_r3_input()
