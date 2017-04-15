import codecs
import json

import time


# TODO use structs
class Codec:
    command_delimiter = b"cwaffle"
    start_delimiter = b"swaffle"
    end_delimiter = b"ewaffle"

    def __init__(self):
        pass

    @classmethod
    def encode(cls, data=b""):
        """
        Encode stream "packet"
        :param data: data to encapsulate
        :return: "packet"
        """
        return cls.start_delimiter + data + cls.end_delimiter

    @classmethod
    def encode_command(cls, name=b"", data=b""):
        """
        Encode command
        :param name: command name
        :param data: extra command data
        :return: packet string
        """
        return name + cls.command_delimiter + data

    @classmethod
    def decode_command(cls, packet=b""):
        """
        Decode command packet
        :param packet: command packet encoded with encode_command(...)
        :return: command, data
        """
        parts = packet.split(cls.command_delimiter)
        return parts[0], parts[1]

    @classmethod
    def decode_input(cls, packet=""):
        data = json.loads(packet)
        data[1] = time.time()
        return data
