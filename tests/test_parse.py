import os

from src.server.data.config_server import ConfigServer
from src.server.net.wii.video import VideoHandler


def test_video_parse():
    """
    Reads dumped video packets and sends them to the video handler
    :return: None
    """
    ConfigServer.load()
    handler = VideoHandler()
    with open(os.path.join(os.path.dirname(__file__), "packets/video.bin"), "rb") as video_packets:
        read = True
        while read:
            packet = b""
            while b"|\n" not in packet:
                read_byte = video_packets.read(1)
                if not read_byte:
                    return
                packet += read_byte
            packet = packet.replace(b"|\n", b"")
            handler.update(packet, True)
