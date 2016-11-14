import array

import construct

from src.common.data import constants
from src.server.net.server.command import ServiceCMD
from src.server.net.wii.base import ServiceBase


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
        self.is_streaming = False
        self.audio_bytes = None

        self.pa_num_bufs = 15
        self.pa_ring = [array.array('H', '\0' * 416 * 2)] * self.pa_num_bufs
        self.pa_wpos = self.pa_rpos = 0

    def close(self):
        self.is_streaming = False

    def parse_audio_stream(self):
        samples = self.pa_ring[self.pa_wpos]
        self.pa_wpos += 1
        self.pa_wpos %= self.pa_num_bufs
        samples.extend(self.pa_ring[self.pa_wpos])
        self.pa_wpos += 1
        self.pa_wpos %= self.pa_num_bufs
        return samples

    def update(self, packet):
        h = self.header.parse(packet)

        # ignore vid_format packets for now
        if h.packet_type == 0:
            seq_ok = self.update_seq_id(h.seq_id)
            if not seq_ok:
                print 'astrm bad seq_id'
            if h.fmt != 1 or h.channel != 0:
                raise Exception('astrm currently only handles 48kHz PCM stereo')
            if len(packet) != 8 + h.payload_size:
                raise Exception('astrm bad payload_size')

            if h.vibrate:
                ServiceCMD.broadcast(constants.COMMAND_VIBRATE)

            self.pa_ring[self.pa_rpos] = array.array('H', packet[8:])
            self.pa_rpos += 1
            self.pa_rpos %= self.pa_num_bufs

            if self.is_streaming:
                self.is_streaming = False
            else:
                self.audio_bytes = self.parse_audio_stream().tostring()
                self.is_streaming = True