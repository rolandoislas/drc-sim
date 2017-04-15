import socket

from src.server.data import constants
from src.server.net.codec import Codec
from src.server.util.logging.logger_backend import LoggerBackend


class Sockets:
    def __init__(self):
        self.WII_MSG_S = None
        self.WII_VID_S = None
        self.WII_AUD_S = None
        self.WII_HID_S = None
        self.WII_CMD_S = None
        self.SERVER_VID_S = None
        self.SERVER_AUD_S = None
        self.SERVER_CMD_S = None
        self.client_sockets = {}

    @staticmethod
    def service_addend(ip):  # TODO this is unnecessary ip is always 192.168.1.11 or empty string
        """
        Client should listen to ports of 100 higher than client
        constants list client ports which commands are sent to
        :param ip: ip of client
        :return: 0 or 100
        """
        if ip == "" or int(ip.split('.')[3]) == 10:
            return 0
        else:
            return 100

    def udp_service(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((ip, port + self.service_addend(ip)))
        except socket.error as e:
            LoggerBackend.throw(e, "Could not create socket for ip %s with port %s" % (ip, port))
        return sock

    # hack for now, replace with dhcp result
    WII_LOCAL_IP = '192.168.1.11'
    SERVER_IP = ''

    @staticmethod
    def tcp_server(ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.listen(5)
        return sock

    def connect(self):
        self.WII_MSG_S = self.udp_service(self.WII_LOCAL_IP, constants.PORT_WII_MSG)
        self.WII_VID_S = self.udp_service(self.WII_LOCAL_IP, constants.PORT_WII_VID)
        self.WII_AUD_S = self.udp_service(self.WII_LOCAL_IP, constants.PORT_WII_AUD)
        self.WII_HID_S = self.udp_service(self.WII_LOCAL_IP, constants.PORT_WII_HID)
        self.WII_CMD_S = self.udp_service(self.WII_LOCAL_IP, constants.PORT_WII_CMD)
        self.SERVER_VID_S = self.tcp_server(self.SERVER_IP, constants.PORT_SERVER_VID)
        self.SERVER_AUD_S = self.tcp_server(self.SERVER_IP, constants.PORT_SERVER_AUD)
        self.SERVER_CMD_S = self.udp_service(self.SERVER_IP, constants.PORT_SERVER_CMD)

    def close(self):
        LoggerBackend.debug("Closing sockets")
        if self.WII_MSG_S:
            # self.WII_MSG_S.shutdown(socket.SHUT_RDWR)
            self.WII_MSG_S.close()
        if self.WII_VID_S:
            # self.WII_VID_S.shutdown(socket.SHUT_RDWR)
            self.WII_VID_S.close()
        if self.WII_AUD_S:
            # self.WII_AUD_S.shutdown(socket.SHUT_RDWR)
            self.WII_AUD_S.close()
        if self.WII_CMD_S:
            # self.WII_CMD_S.shutdown(socket.SHUT_RDWR)
            self.WII_CMD_S.close()
        if self.WII_HID_S:
            # self.WII_HID_S.shutdown(socket.SHUT_RDWR)
            self.WII_HID_S.close()
        if self.SERVER_VID_S:
            # self.SERVER_VID_S.shutdown(socket.SHUT_RDWR)
            self.SERVER_VID_S.close()
        if self.SERVER_AUD_S:
            # self.SERVER_AUD_S.shutdown(socket.SHUT_RDWR)
            self.SERVER_AUD_S.close()
        if self.SERVER_CMD_S:
            # self.SERVER_CMD_S.shutdown(socket.SHUT_RDWR)
            self.SERVER_CMD_S.close()
        LoggerBackend.debug("Closed sockets")

    @classmethod
    def remove_client_socket(cls, address):
        ip = address[0]
        LoggerBackend.debug("Removing client: " + str(ip))
        to_del = []
        for sock_addr in Sockets.client_sockets.keys():
            ip2 = sock_addr[0] if not isinstance(sock_addr[0], socket.socket) else sock_addr[1][0]
            if ip == ip2:
                to_del.append(sock_addr)
        for item in to_del:
            del Sockets.client_sockets[item]
        cls.log_clients()

    @staticmethod
    def log_clients():
        clients = len(Sockets.client_sockets)
        LoggerBackend.debug("Client sockets: %d", clients)
        if clients % 3 == 0:
            LoggerBackend.info("Clients: %d", int(clients / 3))

    @classmethod
    def add_client_socket(cls, sock_addr, handler):
        """
        Add client sockets
        :param sock_addr: tuple (sockeu, address) or address, where address is a tuple (ip, port)
        :param handler: The packet handler
        :return: None
        """
        LoggerBackend.debug("Registered client: " + str(sock_addr))
        Sockets.client_sockets[sock_addr] = handler
        cls.log_clients()

    @staticmethod
    def broadcast_media_packet(packet, socket_type):
        encoded_packet = None
        for sock_addr_pair in list(Sockets.client_sockets.keys()):
            if sock_addr_pair in Sockets.client_sockets.keys() and \
                            Sockets.client_sockets[sock_addr_pair].__name__ == socket_type:
                if not encoded_packet:
                    encoded_packet = Codec.encode(packet)
                try:
                    LoggerBackend.verbose("Broadcast media packet type: %s size: %d" % (socket_type,
                                                                                        len(encoded_packet)))
                    sock_addr_pair[0].sendall(encoded_packet)
                except socket.error:
                    LoggerBackend.verbose("Broadcast media packet failed")
                    Sockets.remove_client_socket(sock_addr_pair[1])

    @staticmethod
    def broadcast_command_packet(command, data, socket_type):
        for address in Sockets.client_sockets.keys():
            if Sockets.client_sockets[address].__name__ == socket_type:
                try:
                    Sockets.SERVER_CMD_S.sendto(Codec.encode_command(command, data), address)
                except socket.error:
                    Sockets.remove_client_socket(address)


Sockets = Sockets()
