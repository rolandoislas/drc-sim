import time

from net import wii_service


class ServiceVID:
    def __init__(self):
        pass

    # noinspection PyUnusedLocal
    @staticmethod
    def update(sock, data):
        # output surface image
        sock.sendall(wii_service.ServiceVSTRM.image_buffer)


class ServiceCMD:
    def __init__(self):
        self.button_buffer, self.l3r3_buffer = (0, 0), (0, 0)
        self.joystick_buffer = ((0, 0, 0, 0), 0)
        self.touch_buffer = (((-1, -1), (-1, -1)), 0)
        self.input_time = 0

    # noinspection PyUnusedLocal
    def update(self, sock, data):
        self.check_button_command(data)
        self.check_l3r3_command(data)

    #  Check Commands

    def check_button_command(self, data):
        self.button_buffer = self.parse_input(self.parse_command("BUTTON", data))

    def check_l3r3_command(self, data):
        self.l3r3_buffer = self.parse_input(self.parse_command("L3R3", data))

    # Getters

    def get_button_input(self):
        if not self.is_input_within_timeframe(self.button_buffer):
            return 0
        return self.button_buffer[0]

    def get_l3_r3_input(self):
        if not self.is_input_within_timeframe(self.l3r3_buffer):
            return 0
        return self.l3r3_buffer[0]

    def get_joystick_input(self, joystick_id):
        if not self.is_input_within_timeframe(self.joystick_buffer):
            return 0
        return self.joystick_buffer[0][joystick_id]

    def get_touch_input(self):
        if not self.is_input_within_timeframe(self.touch_buffer):
            return (-1, -1), (-1, -1)
        return self.touch_buffer[0]

    # Parsers

    @staticmethod
    def parse_command(command, data):
        array = str.split(data, "\n")
        for string in array:
            if string == command:
                return array[array.index(string) + 1]
        return "0"

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
