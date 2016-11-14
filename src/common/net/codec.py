import json

import time


class Codec:
    command_delimiter = "cwaffle"
    start_delimiter = "swaffle"
    end_delimiter = "ewaffle"

    def __init__(self):
        pass

    @classmethod
    def encode(cls, data):
        """
        Encode stream "packet"
        :param data: data to encapsulate
        :return: "packet"
        """
        return cls.start_delimiter + str(data) + cls.end_delimiter

    @classmethod
    def decode(cls, packet):
        """
        Decodes a packet that was encoded using encode(...)
        :param packet: encode(...)  packet
        :return: data bytes
        """
        data = packet.replace(cls.start_delimiter, "").replace(cls.end_delimiter, "")
        data = bytes(data)
        return data

    @classmethod
    def encode_command(cls, name, data):
        """
        Encode command
        :param name: command name
        :param data: extra command data
        :return: packet string
        """
        return str(name) + cls.command_delimiter + str(data)

    @classmethod
    def decode_command(cls, packet):
        """
        Decode command packet
        :param packet: command packet encoded with encode_command(...)
        :return: command, data
        """
        parts = packet.split(cls.command_delimiter)
        return parts[0], parts[1]

    @classmethod
    def decode_input(cls, packet):
        data = json.loads(packet)
        data[1] = time.time()
        return data

    @classmethod
    def encode_input(cls, *args):
        return json.dumps(args)
