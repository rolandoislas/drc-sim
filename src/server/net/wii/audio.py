import codecs
import random

from src.server.control.util.controller import Controller
from src.server.data import constants
from src.server.data.config_server import ConfigServer
from src.server.data.struct import audio
from src.server.net import sockets
from src.server.net.server.audio import ServiceAUD
from src.server.net.server.command import ServiceCMD
from src.server.net.wii.base import ServiceBase
from src.server.util.logging.logger_backend import LoggerBackend


class AudioHandler(ServiceBase):
    def __init__(self):
        super(AudioHandler, self).__init__()
        self.random_audio = ""
        for byte in range(0, 512):
            random_byte = hex(random.randint(0, 255)).replace("0x", "", 1)
            if len(random_byte) == 1:
                self.random_audio += "0"
            self.random_audio += random_byte
        LoggerBackend.debug("Random audio (%d bytes)", len(self.random_audio) / 2)
        LoggerBackend.extra("Random audio: %s", self.random_audio)

    def close(self):
        pass

    def update(self, packet):
        LoggerBackend.verbose("Received audio packet")
        h = audio.header.parse(packet)

        # ignore vid_format packets for now
        if h.packet_type == 0:
            seq_ok = self.update_seq_id(h.seq_id)
            if not seq_ok:
                LoggerBackend.debug('astrm bad seq_id')
            if h.fmt != 1 or h.channel != 0:
                LoggerBackend.throw(Exception('astrm currently only handles 48kHz PCM stereo'))
            if len(packet) != 8 + h.payload_size:
                LoggerBackend.throw(Exception('astrm bad payload_size'))

            if h.vibrate:
                ServiceCMD.broadcast(constants.COMMAND_VIBRATE)

            if ConfigServer.stream_audio:
                ServiceAUD.broadcast(packet[8:])

            if Controller.get_send_audio():
                self.send_audio(h.seq_id)

    def send_audio(self, sid):
        header = audio.header.build(dict(
            fmt=6,
            channel=1,
            vibrate=False,
            packet_type=0,
            seq_id=sid,
            payload_size=512,
            timestamp=0
        ))
        data = codecs.decode(self.random_audio, "hex")
        sockets.Sockets.WII_AUD_S.sendto(header + data, ('192.168.1.10', constants.PORT_WII_AUD))
