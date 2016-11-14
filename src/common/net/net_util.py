import socket
import time

from src.common.net.codec import Codec


class NetUtil:
    def __init__(self):
        self.stream = ""

    def recv(self, sock):
        while Codec.end_delimiter not in self.stream:
            data = sock.recv(100000)  # The buffer will only be this big on uncompressed loopback most likely
            if not data:
                self.stream = ""
                raise socket.error
            self.stream += data
        index = self.stream.find(Codec.end_delimiter)
        packet = self.stream[0:index]
        self.stream = self.stream[index + len(Codec.end_delimiter):]
        return Codec.decode(packet)

NetUtil = NetUtil()
