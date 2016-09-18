import pygame
import time

class ServiceVID:
    def __init__(self):
        pass

    # noinspection PyUnusedLocal
    @staticmethod
    def update(sock, data):
        # output surface image
        image_buffer = pygame.image.tostring(pygame.display.get_surface(), "RGB", False)
        sock.sendall(image_buffer)


class ServiceCMD:
    def __init__(self):
        self.input_buffer, self.l3r3_buffer, self.input_time = (0, 0), (0, 0), 0

    # noinspection PyUnusedLocal
    def update(self, sock, data):
        self.check_button_command(data)
        self.check_l3r3_command(data)

    @staticmethod
    def parse_command(command, data):
        array = str.split(data, "\n")
        for string in array:
            if string == command:
                return array[array.index(string) + 1]
        return "0"

    def check_button_command(self, data):
        self.input_buffer = self.parse_input(self.parse_command("BUTTON", data))

    def check_l3r3_command(self, data):
        self.l3r3_buffer = self.parse_input(self.parse_command("L3R3", data))

    def get_input(self):
        if not self.is_input_within_timeframe(self.input_buffer):
            return 0
        return self.input_buffer[0]

    def get_l3_r3_input(self):
        if not self.is_input_within_timeframe(self.l3r3_buffer):
            return 0
        return self.l3r3_buffer[0]

    @staticmethod
    def parse_input(data):
        array = str.split(data, "-")
        if len(array) < 2:
            return 0, 0
        return int(array[0]), float(array[1])

    @staticmethod
    def is_input_within_timeframe(input_buffer):
        if time.time() - input_buffer[1] <= 0.1:
            return True
        return False

ServiceCMD = ServiceCMD()
