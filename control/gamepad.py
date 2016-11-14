import socket

import array

import time

from control import controller
from net import socket_handlers
from net import sockets


class Gamepad:
    def __init__(self):
        self.hid_seq_id = 0
        self.hid_update_timestamp = 0
        self.HID_UPDATE_INTERVAL = int((1. / 180.) * 1000.)  # 5 - leaving it since it may make sense later
        sockets.Sockets.connect()
        socket_handlers.SocketHandlers.create()

    def send_hid_update(self):

        report = array.array('H', '\0\0' * 0x40)

        # 16bit LE @ 0 seq_id
        # seems to be ignored
        report[0] = self.hid_seq_id

        report = controller.get_button_input_report(report)
        report = controller.get_l3_r3_input_report(report)
        report = controller.get_joystick_input_report(report)
        report = controller.get_touch_input_report(report)

        # 16bit @ 126
        report[0x3f] = 0xe000
        # print report.tostring().encode('hex')
        sockets.Sockets.WII_HID_S.sendto(report, ('192.168.1.10', constants.WII_PORT_HID))
        self.hid_seq_id = (self.hid_seq_id + 1) % 65535

    def check_send_hid(self):
        timestamp = time.time() * 1000.
        if timestamp - self.hid_update_timestamp >= self.HID_UPDATE_INTERVAL:
            self.hid_update_timestamp = timestamp
            self.send_hid_update()

    @staticmethod
    def handle_wii_packet(sock):
        data = sock.recv(2048)
        try:
            socket_handlers.SocketHandlers.service_handlers[sock].update(data)
        except socket.error, e:
            print str(e) + str(e.errno)

    @staticmethod
    def add_client_socket(sock):
        client, address = sock.accept()
        sockets.Sockets.client_sockets[client] = socket_handlers.SocketHandlers.server_handlers[sock]

    @staticmethod
    def handle_client_packet(sock):
        try:
            data = sock.recv(2048)
        except socket.error:
            del sockets.Sockets.client_sockets[sock]
        else:
            if not data:
                del sockets.Sockets.client_sockets[sock]
            else:
                sockets.Sockets.client_sockets[sock].update(sock, data)

    def handle_sockets(self):
        # Group all sockets
        rlist, wlist, xlist = select.select(socket_handlers.SocketHandlers.service_handlers.keys() +
                                            socket_handlers.SocketHandlers.server_handlers.keys() +
                                            sockets.Sockets.client_sockets.keys(),
                                            (), (), 1)
        if rlist:
            for sock in rlist:
                # Wii socket
                if sock in socket_handlers.SocketHandlers.service_handlers.keys():
                    self.handle_wii_packet(sock)
                # Server socket
                if sock in socket_handlers.SocketHandlers.server_handlers.keys():
                    self.add_client_socket(sock)
                # Client socket
                if sock in sockets.Sockets.client_sockets.keys():
                    self.handle_client_packet(sock)

    def update(self):
        self.check_send_hid()
        self.handle_sockets()

    def close(self):
        for s in socket_handlers.SocketHandlers.service_handlers.itervalues():
            s.close()
