import lz4

from data.config import Config


class Codec:
    delimiter = "waffle"
    header_delimiter = "|"

    def __init__(self):
        pass

    @classmethod
    def encode(cls, data):
        if Config.compress_data:
            data = lz4.compress(data)
        header = len(data)
        return cls.delimiter + str(header) + cls.delimiter + str(data)

    @classmethod
    def decode_packet_header(cls, packet):
        data = str.split(packet, cls.delimiter)
        if len(data) < 3:
            raise ValueError("Packet does not conform to encoding standard")
        header_size = len(data[0]) + len(data[1]) + len(cls.delimiter) * 2
        data_size = int(data[1])
        return header_size, data_size

    @classmethod
    def decode(cls, packet):
        data = str.split(packet, cls.delimiter)[2]
        if Config.compress_data:
            data = lz4.decompress(data)
        return bytes(data)
