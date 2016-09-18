import array
import pygame
import select
import socket

import psutil

from control import controller
from data import constants
from net import server_service
from net import wii_service

pygame.init()
pygame.display.set_mode([854, 480], pygame.RESIZABLE)
pygame.display.set_caption("drc-sim")
done = False


def service_addend(ip):
    if int(ip.split('.')[3]) == 10:
        return 0
    else:
        return 100


def udp_service(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port + service_addend(ip)))
    return sock

# hack for now, replace with dhcp result
WII_LOCAL_IP = '192.168.1.11'
SERVER_IP = '0.0.0.0'

WII_MSG_S = udp_service(WII_LOCAL_IP, constants.WII_PORT_MSG)
WII_VID_S = udp_service(WII_LOCAL_IP, constants.WII_PORT_VID)
WII_AUD_S = udp_service(WII_LOCAL_IP, constants.WII_PORT_AUD)
WII_HID_S = udp_service(WII_LOCAL_IP, constants.WII_PORT_HID)
WII_CMD_S = udp_service(WII_LOCAL_IP, constants.WII_PORT_CMD)


def server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip, port))
    sock.listen(5)
    return sock

SERVER_VID_S = server(SERVER_IP, constants.SERVER_PORT_VID)
SERVER_CMD_S = server(SERVER_IP, constants.SERVER_PORT_CMD)

wii_service.init(WII_CMD_S, constants.WII_PORT_CMD, WII_MSG_S, constants.WII_PORT_MSG)
service_handlers = {
    WII_MSG_S: wii_service.ServiceMSG(),
    WII_VID_S: wii_service.ServiceVSTRM(),
    WII_AUD_S: wii_service.ServiceASTRM(),
    WII_CMD_S: wii_service.ServiceCMD(),
}

server_handlers = {
    SERVER_VID_S: server_service.ServiceVID(),
    SERVER_CMD_S: server_service.ServiceCMD
}

client_sockets = {}

hid_seq_id = 0


def hid_snd():
    global hid_seq_id

    report = array.array('H', '\0\0' * 0x40)

    # 16bit LE @ 0 seq_id
    # seems to be ignored
    report[0] = hid_seq_id
    # 16bit @ 2
    button_bits = 0
    # Get input
    button_bits |= controller.get_input()
    report[40] |= controller.get_l3_r3_input()

    # 16bit LE array @ 6
    # LX, LY, RX, RY
    # 0: l stick l/r
    # 1: l stick u/d
    # 2: l trigger
    # 3: r stick l/r
    # 4: r stick u/d
    # 5: r trigger
    def scale_stick(old_value, old_min, old_max, new_min, new_max):
        return int((((old_value - old_min) * (new_max - new_min)) / (old_max - old_min)) + new_min)

    for i in xrange(6):
        if i not in (2, 5):
            orig = 0
            scaled = 0x800
            if abs(orig) > 0.2:
                if i in (0, 3):
                    scaled = scale_stick(orig, -1, 1, 900, 3200)
                elif i in (1, 4):
                    scaled = scale_stick(orig, 1, -1, 900, 3200)
            # print '%04i %04i %f' % (i, scaled, orig)
            stick_mapping = {0: 0, 1: 1, 3: 2, 4: 3}
            report[3 + stick_mapping[i]] = scaled
    report[1] = (button_bits >> 8) | ((button_bits & 0xff) << 8)

    # touchpanel crap @ 36 - 76 FIXME Wii U registers input, but touch event does not seem to happen. Wrong coords?
    # byte_18 = 0
    byte_17 = 3
    # byte_9b8 = 0
    byte_9fd = 6
    umi_fw_rev = 0x40
    # byte_9fb = 0
    byte_19 = 2
    if pygame.mouse.get_pressed()[0]:
        point = pygame.mouse.get_pos()
        screen_x, screen_y = pygame.display.get_surface().get_size()
        x = scale_stick(point[0], 0, screen_x, 200, 3800)
        y = scale_stick(point[1], 0, screen_y, 200, 3800)
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

    # 8bit @ 80

    report[0x3f] = 0xe000
    # print report.tostring().encode('hex')
    WII_HID_S.sendto(report, ('192.168.1.10', constants.WII_PORT_HID))
    hid_seq_id = (hid_seq_id + 1) % 65535


EVT_SEND_HID = pygame.USEREVENT
pygame.time.set_timer(EVT_SEND_HID, int((1. / 180.) * 1000.))


def check_events():
    global done
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        elif event.type == pygame.VIDEORESIZE:
            pygame.display.set_mode(event.size, pygame.RESIZABLE)
            service_handlers[WII_VID_S].resize_output(event.size)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSLASH:
                WII_MSG_S.sendto('\1\0\0\0', ('192.168.1.10', constants.WII_PORT_MSG))
        elif event.type == EVT_SEND_HID:
            hid_snd()


def handle_wii_socket(sock):
    data = sock.recv(2048)
    service_handlers[sock].update(data)


def handle_server_socket(sock):
    client, address = sock.accept()
    client_sockets[client] = server_handlers[sock]


def handle_client_socket(sock):
    data = sock.recv(2048)
    if data:
        client_sockets[sock].update(sock, data)
    else:
        del client_sockets[sock]


def handle_sockets():
    # Group all sockets
    rlist, wlist, xlist = select.select(service_handlers.keys() + server_handlers.keys() + client_sockets.keys(),
                                        (), (), 1)
    if rlist:
        for sock in rlist:
            # Wii socket
            if sock in service_handlers.keys():
                handle_wii_socket(sock)
            # Server socket
            if sock in server_handlers.keys():
                handle_server_socket(sock)
            # Client socket
            if sock in client_sockets.keys():
                handle_client_socket(sock)


# FIXME there might be a leak somewhere
def check_memory():
    if psutil.virtual_memory().percent >= 85:
        raise MemoryError("Memory usage is high. Quitting.")


def loop():
    check_memory()
    check_events()
    handle_sockets()


while not done:
    loop()

for s in service_handlers.itervalues():
    s.close()

pygame.quit()
