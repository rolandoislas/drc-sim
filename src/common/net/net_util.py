import socket

from src.common.net.codec import Codec


class NetUtil:
    def __init__(self):
        self.buffers = {}

    def recv(self, sock, buffer_id):
        if buffer_id not in self.buffers.keys():
            self.buffers[buffer_id] = ""
        while Codec.end_delimiter not in self.buffers[buffer_id]:
            data = sock.recv(100000)  # The buffer will only be this big on uncompressed loopback most likely
            if not data:
                self.buffers = {}
                raise socket.error
            self.buffers[buffer_id] += data
        index = self.buffers[buffer_id].find(Codec.end_delimiter)
        packet = self.buffers[buffer_id][0:index]
        self.buffers[buffer_id] = self.buffers[buffer_id][index + len(Codec.end_delimiter):]
        return Codec.decode(packet)

NetUtil = NetUtil()
