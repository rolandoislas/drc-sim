from src.server.data import constants
from src.server.data.config_server import ConfigServer
from src.server.data.struct import audio
from src.server.net.server.audio import ServiceAUD
from src.server.net.server.command import ServiceCMD
from src.server.net.wii.base import ServiceBase
from src.server.util.logging.logger_backend import LoggerBackend


class AudioHandler(ServiceBase):
    def __init__(self):
        super(AudioHandler, self).__init__()

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
