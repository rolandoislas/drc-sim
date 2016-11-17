import array
import time

from src.common.data import constants
from src.common.net.codec import Codec
from src.server.data.config import ConfigServer
from src.server.net import sockets


class Controller:
    hid_seq_id = 0
    hid_update_timestamp = 0
    HID_UPDATE_INTERVAL = int((1. / 180.) * 1000.)  # 5 - leaving it since it may make sense later
    # Button buffers
    button_buffer = (0, 0)
    l3r3_buffer = (0, 0)
    joystick_buffer = ((0, 0, 0, 0, 0), 0)
    touch_buffer = (((-1, -1), (-1, -1)), 0)

    def __init__(self):
        pass

    # The following get_####_input_report methods modify a passed report array

    @classmethod
    def get_button_input_report(cls, report):
        button_bits = cls.get_button_input()
        # 16bit @ 2
        report[1] = (button_bits >> 8) | ((button_bits & 0xff) << 8)
        return report

    @classmethod
    def get_l3_r3_input_report(cls, report):
        # 8bit @ 80
        l3r3_bits = cls.get_l3_r3_input()
        report[40] = l3r3_bits
        return report

    @classmethod
    def scale_stick(cls, old_value, old_min, old_max, new_min, new_max):
        return int((((old_value - old_min) * (new_max - new_min)) / (old_max - old_min)) + new_min)

    @classmethod
    def get_joystick_input_report(cls, report):
        # 16bit LE array @ 6
        # LX, LY, RX, RY
        # 0: l stick l/r
        # 1: l stick u/d
        # 2: l trigger
        # 3: r stick l/r
        # 4: r stick u/d
        # 5: r trigger
        for i in xrange(6):
            if i not in (2, 5):
                orig = cls.get_joystick_input(i)
                scaled = 0x800
                if abs(orig) > 0.2:
                    if i in (0, 3):
                        scaled = cls.scale_stick(orig, -1, 1, 900, 3200)
                    elif i in (1, 4):
                        scaled = cls.scale_stick(orig, 1, -1, 900, 3200)
                # print '%04i %04i %f' % (i, scaled, orig)
                stick_mapping = {0: 0, 1: 1, 3: 2, 4: 3}
                report[3 + stick_mapping[i]] = scaled
        return report

    @classmethod
    def get_touch_input_report(cls, report):
        # touchpanel crap @ 36 - 76
        # byte_18 = 0
        byte_17 = 3
        # byte_9b8 = 0
        byte_9fd = 6
        umi_fw_rev = 0x40
        # byte_9fb = 0
        byte_19 = 2
        point, screen = cls.get_touch_input()
        if point[0] >= 0 and point[1] >= 0:
            x = cls.scale_stick(point[0], 0, screen[0], 200, 3800)
            y = cls.scale_stick(point[1], 0, screen[1], 3800, 200)
            z1 = 2000

            for i in xrange(10):
                report[18 + i * 2 + 0] = 0x8000 | x
                report[18 + i * 2 + 1] = 0x8000 | y

            report[18 + 0 * 2 + 0] |= ((z1 >> 0) & 7) << 12
            report[18 + 0 * 2 + 1] |= ((z1 >> 3) & 7) << 12
            report[18 + 1 * 2 + 0] |= ((z1 >> 6) & 7) << 12
            report[18 + 1 * 2 + 1] |= ((z1 >> 9) & 7) << 12

        report[18 + 3 * 2 + 1] |= ((byte_17 >> 0) & 7) << 12
        report[18 + 4 * 2 + 0] |= ((byte_17 >> 3) & 7) << 12
        report[18 + 4 * 2 + 1] |= ((byte_17 >> 6) & 3) << 12

        report[18 + 5 * 2 + 0] |= ((byte_9fd >> 0) & 7) << 12
        report[18 + 5 * 2 + 1] |= ((byte_9fd >> 3) & 7) << 12
        report[18 + 6 * 2 + 0] |= ((byte_9fd >> 6) & 3) << 12

        report[18 + 7 * 2 + 0] |= ((umi_fw_rev >> 4) & 7) << 12

        # TODO checkout what's up with | 4
        report[18 + 9 * 2 + 1] |= ((byte_19 & 2) | 4) << 12
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
    def get_l3_r3_input(cls):
        if not cls.is_input_within_timeframe(cls.l3r3_buffer):
            return 0
        return cls.l3r3_buffer[0]

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
    def set_button_input(cls, data):
        cls.button_buffer = Codec.decode_input(data)

    @classmethod
    def set_l3r3_input(cls, data):
        cls.l3r3_buffer = Codec.decode_input(data)

    @classmethod
    def set_touch_input(cls, data):
        cls.touch_buffer = Codec.decode_input(data)

    @classmethod
    def set_joystick_input(cls, data):
        cls.joystick_buffer = Codec.decode_input(data)

    #  Update

    @classmethod
    def send_hid_update(cls):

        report = array.array('H', '\0\0' * 0x40)

        # 16bit LE @ 0 seq_id
        # seems to be ignored
        report[0] = cls.hid_seq_id

        report = cls.get_button_input_report(report)
        report = cls.get_l3_r3_input_report(report)
        report = cls.get_joystick_input_report(report)
        report = cls.get_touch_input_report(report)

        # 16bit @ 126
        report[0x3f] = 0xe000
        # print report.tostring().encode('hex')
        sockets.Sockets.WII_HID_S.sendto(report, ('192.168.1.10', constants.PORT_WII_HID))
        cls.hid_seq_id = (cls.hid_seq_id + 1) % 65535

    @classmethod
    def update(cls):
        timestamp = time.time() * 1000.
        if timestamp - cls.hid_update_timestamp >= cls.HID_UPDATE_INTERVAL:
            cls.hid_update_timestamp = timestamp
            cls.send_hid_update()
