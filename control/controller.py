from net import server_service

try:
    # noinspection PyUnresolvedReferences
    from control import keyboard
except ImportError:
    print "This is the backend or pygame is not installed."
else:

    # The get_####_input methods provide the raw data to be put into the report
    # This is useful a frontend that does not construct the report


    def get_button_input(server=False):
        if server:
            return server_service.ServiceCMD.get_button_input()
        return keyboard.get_button_input()


    def get_l3_r3_input(server=False):
        if server:
            return server_service.ServiceCMD.get_l3_r3_input()
        return keyboard.get_l3_r3_input()


    def get_joystick_input(joystick_id, server=False):
        if server:
            return server_service.ServiceCMD.get_joystick_input(joystick_id)
        return keyboard.get_joystick_input(joystick_id)


    def get_touch_input(server=False):
        if server:
            return server_service.ServiceCMD.get_touch_input()
        return keyboard.get_touch_input()

# The following get_####_input_report methods modify a passed report array
# Used only on the backend


def get_button_input_report(report):
    # TODO detect and send other inputs
    button_bits = get_button_input(True)
    # 16bit @ 2
    report[1] = (button_bits >> 8) | ((button_bits & 0xff) << 8)
    return report


def get_l3_r3_input_report(report):
    # 8bit @ 80
    l3r3_bits = get_l3_r3_input(True)
    report[40] = l3r3_bits
    return report


def scale_stick(old_value, old_min, old_max, new_min, new_max):
    return int((((old_value - old_min) * (new_max - new_min)) / (old_max - old_min)) + new_min)


def get_joystick_input_report(report):
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
            orig = get_joystick_input(i, True)
            scaled = 0x800
            if abs(orig) > 0.2:
                if i in (0, 3):
                    scaled = scale_stick(orig, -1, 1, 900, 3200)
                elif i in (1, 4):
                    scaled = scale_stick(orig, 1, -1, 900, 3200)
            # print '%04i %04i %f' % (i, scaled, orig)
            stick_mapping = {0: 0, 1: 1, 3: 2, 4: 3}
            report[3 + stick_mapping[i]] = scaled
    return report


def get_touch_input_report(report):
    # touchpanel crap @ 36 - 76 FIXME Wii U registers input, but touch event does not seem to happen. Wrong coords?
    # byte_18 = 0
    byte_17 = 3
    # byte_9b8 = 0
    byte_9fd = 6
    umi_fw_rev = 0x40
    # byte_9fb = 0
    byte_19 = 2
    point, screen = get_touch_input(True)
    if point[0] >= 0 and point[1] >= 0:
        x = scale_stick(point[0], 0, screen[0], 200, 3800)
        y = scale_stick(point[1], 0, screen[1], 200, 3800)
        z1 = 2000

        for i in xrange(10):
            report[18 + i * 2 + 0] = 0x80 | x
            report[18 + i * 2 + 1] = 0x80 | y

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
