import construct

from src.server.data import constants
from src.server.data.config_server import ConfigServer
from src.server.net.server.audio import ServiceAUD
from src.server.net.server.command import ServiceCMD
from src.server.net.wii.base import ServiceBase
from src.server.util.logging.logger_backend import LoggerBackend


class AudioHandler(ServiceBase):
    def __init__(self):
        super(AudioHandler, self).__init__()
        self.header_base = construct.BitStruct('ASTRMBaseHeader',
                                               construct.BitField('fmt', 3),
                                               construct.Bit('channel'),
                                               construct.Flag('vibrate'),
                                               construct.Bit('packet_type'),
                                               construct.BitField('seq_id', 10),
                                               construct.BitField('payload_size', 16)
                                               )
        self.header_aud = construct.Struct('ASTRMAudioHeader',
                                           construct.ULInt32('timestamp')
                                           )
        self.header_msg = construct.Struct('ASTRMMsgHeader',
                                           # This is kind of a hack, (there are two timestamp fields, which one is used
                                           # depends on packet_type
                                           construct.ULInt32('timestamp_audio'),
                                           construct.ULInt32('timestamp'),
                                           construct.Array(2, construct.ULInt32('freq_0')),  # -> mc_video
                                           construct.Array(2, construct.ULInt32('freq_1')),  # -> mc_sync
                                           construct.ULInt8('vid_format'),
                                           construct.Padding(3)
                                           )
        self.header = construct.Struct('ASTRMHeader',
                                       construct.Embed(self.header_base),
                                       construct.Switch('format_hdr', lambda ctx: ctx.packet_type,
                                                        {
                                                            0: construct.Embed(self.header_aud),
                                                            1: construct.Embed(self.header_msg),
                                                        },
                                                        default=construct.Pass
                                                        )
                                       )

    def close(self):
        pass

    def update(self, packet):
        LoggerBackend.verbose("Received audio packet")
        h = self.header.parse(packet)

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
