import array
import select
import socket
import time

import psutil

from control import controller
from data import constants
from net import server_service
from net import wii_service


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
SERVER_AUD_S = server(SERVER_IP, constants.SERVER_PORT_AUD)
SERVER_CMD_S = server(SERVER_IP, constants.SERVER_PORT_CMD)

wii_service.init(WII_CMD_S, constants.WII_PORT_CMD, WII_MSG_S, constants.WII_PORT_MSG)
service_handlers = {
    WII_MSG_S: wii_service.ServiceMSG(),
    WII_VID_S: wii_service.ServiceVSTRM,
    WII_AUD_S: wii_service.ServiceASTRM,
    WII_CMD_S: wii_service.ServiceCMD(),
}

server_handlers = {
    SERVER_VID_S: server_service.ServiceVID(),
    SERVER_AUD_S: server_service.ServiceAUD(),
    SERVER_CMD_S: server_service.ServiceCMD
}

client_sockets = {}

hid_seq_id = 0
hid_update_timestamp = 0
HID_UPDATE_INTERVAL = int((1. / 180.) * 1000.)  # 5 - leaving it since it may make sense later


def send_hid_update():
    global hid_seq_id

    report = array.array('H', '\0\0' * 0x40)

    # 16bit LE @ 0 seq_id
    # seems to be ignored
    report[0] = hid_seq_id

    report = controller.get_button_input_report(report)
    report = controller.get_l3_r3_input_report(report)
    report = controller.get_joystick_input_report(report)
    report = controller.get_touch_input_report(report)

    # 16bit @ 126
    report[0x3f] = 0xe000
    # print report.tostring().encode('hex')
    WII_HID_S.sendto(report, ('192.168.1.10', constants.WII_PORT_HID))
    hid_seq_id = (hid_seq_id + 1) % 65535


def check_send_hid():
    global hid_update_timestamp
    timestamp = time.time() * 1000.
    if timestamp - hid_update_timestamp >= HID_UPDATE_INTERVAL:
        hid_update_timestamp = timestamp
        send_hid_update()


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


# FIXME there IS a leak in the audio service parse_audio_stream()
def check_memory():
    if psutil.virtual_memory().percent >= 85:
        raise MemoryError("Memory usage is high. Quitting.")


def loop():
    check_memory()
    check_send_hid()
    handle_sockets()


while True:
    loop()

for s in service_handlers.itervalues():
    s.close()
