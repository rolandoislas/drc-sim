import time

import array

from src.server.data import constants
from src.server.data.config_server import ConfigServer
from src.server.data.struct import input
from src.server.net import sockets
from src.server.net.codec import Codec


class Controller:
    hid_seq_id = 0
    hid_update_timestamp = 0
    HID_UPDATE_INTERVAL = int((1 / 10) * 1000)  # should be 180 per second FIXME python 3 sockets are slow
    # Button buffers
    button_buffer = (0, 0)
    extra_button_buffer = (0, 0)
    joystick_buffer = ((0, 0, 0, 0), 0)
    touch_buffer = (((-1, -1), (-1, -1)), 0)
    send_audio = (False, 0)

    def __init__(self):
        pass

    @classmethod
    def scale_stick(cls, old_value, old_min, old_max, new_min, new_max):
        return int((((old_value - old_min) * (new_max - new_min)) / (old_max - old_min)) + new_min)

    @classmethod
    def get_touch_input_report(cls, report):
        point, screen = cls.get_touch_input()
        if point[0] >= 0 and point[1] >= 0:
            x = cls.scale_stick(point[0], 0, screen[0], 200, 3800)
            y = cls.scale_stick(point[1], 0, screen[1], 3800, 200)
            z1 = 2000

            for i in range(10):
                report[18 + i * 2 + 0] = 0x8000 | x
                report[18 + i * 2 + 1] = 0x8000 | y

            report[18 + 0 * 2 + 0] |= ((z1 >> 0) & 7) << 12
            report[18 + 0 * 2 + 1] |= ((z1 >> 3) & 7) << 12
            report[18 + 1 * 2 + 0] |= ((z1 >> 6) & 7) << 12
            report[18 + 1 * 2 + 1] |= ((z1 >> 9) & 7) << 12
        return report

    # Getters

    @classmethod
    def is_input_within_timeframe(cls, input_buffer):
        if time.time() - input_buffer[1] <= ConfigServer.input_delay:
            return True
        return False

    @classmethod
    def get_button_input(cls):
        if not cls.is_input_within_timeframe(cls.button_buffer):
            return 0
        return cls.button_buffer[0]

    @classmethod
    def get_extra_button_input(cls):
        if not cls.is_input_within_timeframe(cls.extra_button_buffer):
            return 0
        return cls.extra_button_buffer[0]

    @classmethod
    def get_joystick_input(cls, joystick_id):
        if not cls.is_input_within_timeframe(cls.joystick_buffer):
            return 0
        return cls.joystick_buffer[0][joystick_id]

    @classmethod
    def get_touch_input(cls):
        if not cls.is_input_within_timeframe(cls.touch_buffer):
            return (-1, -1), (-1, -1)
        return cls.touch_buffer[0]

    @classmethod
    def get_send_audio(cls):
        if not cls.is_input_within_timeframe(cls.send_audio):
            return False
        return cls.send_audio

    @classmethod
    def set_button_input(cls, data):
        cls.button_buffer = Codec.decode_input(data)

    @classmethod
    def set_extra_button_input(cls, data):
        cls.extra_button_buffer = Codec.decode_input(data)

    @classmethod
    def set_touch_input(cls, data):
        cls.touch_buffer = Codec.decode_input(data)

    @classmethod
    def set_joystick_input(cls, data):
        cls.joystick_buffer = Codec.decode_input(data)

    @classmethod
    def set_send_audio(cls, data):
        cls.send_audio = Codec.decode_input(data)

    @classmethod
    def send_hid_update(cls):
        report_array = array.array("H", b"\x00" * input.input_data.sizeof())
        report_array = cls.get_touch_input_report(report_array)  # TODO handle this in the struct
        report = input.input_data.parse(report_array.tobytes())

        report.sequence_id = cls.hid_seq_id
        report.buttons = cls.get_button_input()
        report.power_status = 0
        report.battery_charge = 0
        report.extra_buttons = cls.get_extra_button_input()
        report.left_stick_x = 8 + int(cls.get_joystick_input(0) * 8)
        report.left_stick_y = 8 - int(cls.get_joystick_input(1) * 8)
        report.right_stick_x = 8 + int(cls.get_joystick_input(2) * 8)
        report.right_stick_y = 8 - int(cls.get_joystick_input(3) * 8)
        report.audio_volume = 0
        report.accel_x = 0
        report.accel_y = 0
        report.accel_z = 0
        report.gyro_roll = 0
        report.gyro_yaw = 0
        report.gyro_pitch = 0
        report.fw_version_neg = 215

        sockets.Sockets.WII_HID_S.sendto(input.input_data.build(report), ('192.168.1.10', constants.PORT_WII_HID))
        cls.hid_seq_id = (cls.hid_seq_id + 1) % 65535

    @classmethod
    def update(cls):
        timestamp = time.time() * 1000.
        if timestamp - cls.hid_update_timestamp >= cls.HID_UPDATE_INTERVAL:
            cls.hid_update_timestamp = timestamp
            cls.send_hid_update()
