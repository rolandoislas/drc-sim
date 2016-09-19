import array
import time

import construct

from data.h264decoder import H264Decoder

WII_CMD_S, WII_PORT_CMD, WII_MSG_S, WII_PORT_MSG = None, None, None, None


class ServiceBase(object):
    def __init__(self):
        self.seq_id_expect = None

    def update_seq_id(self, seq_id):
        ret = True
        if self.seq_id_expect is None:
            self.seq_id_expect = seq_id
        elif self.seq_id_expect != seq_id:
            ret = False
        self.seq_id_expect = (seq_id + 1) & 0x3ff
        return ret

    def close(self):
        pass


class ServiceASTRM(ServiceBase):
    def __init__(self):
        super(ServiceASTRM, self).__init__()
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
        self.sample = None

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
                print '*vibrate*'

            self.pa_ring[self.pa_rpos] = array.array('H', packet[8:])
            self.pa_rpos += 1
            self.pa_rpos %= self.pa_num_bufs

            if self.is_streaming:
                self.is_streaming = False
            else:
                audio_bytes = self.parse_audio_stream()
                self.sample = (audio_bytes.tostring(), time.time())
                self.is_streaming = True

ServiceASTRM = ServiceASTRM()


class ServiceVSTRM(ServiceBase):
    def __init__(self):
        super(ServiceVSTRM, self).__init__()
        self.decoder = H264Decoder()
        self.header = construct.BitStruct('VSTRMHeader',
                                          construct.Nibble('magic'),
                                          construct.BitField('packet_type', 2),
                                          construct.BitField('seq_id', 10),
                                          construct.Flag('init'),
                                          construct.Flag('frame_begin'),
                                          construct.Flag('chunk_end'),
                                          construct.Flag('frame_end'),
                                          construct.Flag('has_timestamp'),
                                          construct.BitField('payload_size', 11),
                                          construct.BitField('timestamp', 32)
                                          )
        self.frame = array.array('B')
        self.is_streaming = False
        self.frame_decode_num = 0
        self.image_buffer = None

    def close(self):
        self.decoder.close()

    @staticmethod
    def packet_is_idr(packet):
        return packet[8:16].find('\x80') != -1

    def h264_nal_encapsulate(self, is_idr, vstrm):
        slice_header = 0x25b804ff if is_idr else (0x21e003ff | ((self.frame_decode_num & 0xff) << 13))
        self.frame_decode_num += 1

        nals = array.array('B')
        # TODO shouldn't really need this after the first IDR
        # TODO hardcoded for gamepad for now
        # allow decoder to know stream parameters
        if is_idr:
            nals.extend([
                # sps
                0x00, 0x00, 0x00, 0x01,
                0x67, 0x64, 0x00, 0x20, 0xac, 0x2b, 0x40, 0x6c, 0x1e, 0xf3, 0x68,
                # pps
                0x00, 0x00, 0x00, 0x01,
                0x68, 0xee, 0x06, 0x0c, 0xe8
            ])

        # begin slice nalu
        nals.extend([0x00, 0x00, 0x00, 0x01])
        nals.extend([(slice_header >> 24) & 0xff,
                     (slice_header >> 16) & 0xff,
                     (slice_header >> 8) & 0xff,
                     slice_header & 0xff])

        # add escape codes
        nals.extend(vstrm[:2])
        for i in xrange(2, len(vstrm)):
            if vstrm[i] <= 3 and nals[-2] == 0 and nals[-1] == 0:
                nals.extend([3])
            nals.extend([vstrm[i]])

        return nals

    def update(self, packet):
        h = self.header.parse(packet)
        is_idr = self.packet_is_idr(packet)

        seq_ok = self.update_seq_id(h.seq_id)

        if not seq_ok:
            self.is_streaming = False

        if h.frame_begin:
            self.frame = array.array('B')
            if not self.is_streaming:
                if is_idr:
                    self.is_streaming = True
                else:
                    # request a new IDR frame
                    WII_MSG_S.sendto('\1\0\0\0', ('192.168.1.10', WII_PORT_MSG))
                    return

        self.frame.fromstring(packet[16:])

        if self.is_streaming and h.frame_end:
            # update image
            nals = self.h264_nal_encapsulate(is_idr, self.frame)
            self.image_buffer = self.decoder.get_image_buffer(nals.tostring())

ServiceVSTRM = ServiceVSTRM()


class ServiceCMD(ServiceBase):
    PT_REQ = 0
    PT_REQ_ACK = 1
    PT_RESP = 2
    PT_RESP_ACK = 3

    CMD0_OK = 0

    def __init__(self):
        super(ServiceCMD, self).__init__()
        self.header_cmd0 = construct.Struct('CMD0Header',
                                            construct.UBInt8('magic'),
                                            construct.UBInt8('unk_0'),
                                            construct.UBInt8('unk_1'),
                                            construct.UBInt8('unk_2'),
                                            construct.UBInt8('unk_3'),
                                            construct.UBInt8('flags'),
                                            construct.UBInt8('id_primary'),
                                            construct.UBInt8('id_secondary'),
                                            construct.UBInt16('error_code'),
                                            construct.UBInt16('payload_size_cmd0')
                                            )
        self.header_cmd1 = construct.Struct('CMD1Header',
                                            construct.Padding(48)
                                            )
        self.header_cmd2 = construct.Struct('CMD2Header',
                                            construct.ULInt16('JDN_base'),
                                            construct.Padding(2),
                                            construct.ULInt32('seconds')
                                            )
        self.header = construct.Struct('CMDHeader',
                                       construct.ULInt16('packet_type'),
                                       construct.ULInt16('cmd_id'),
                                       construct.ULInt16('payload_size'),
                                       construct.ULInt16('seq_id'),
                                       construct.Switch('cmd_hdr', lambda ctx: ctx.cmd_id,
                                                        {
                                                            0: construct.If(
                                                                lambda
                                                                ctx: ctx.payload_size >= self.header_cmd0.sizeof(),
                                                                construct.Embed(self.header_cmd0)),
                                                            1: construct.If(
                                                                lambda
                                                                ctx: ctx.payload_size == self.header_cmd1.sizeof(),
                                                                construct.Embed(self.header_cmd1)),
                                                            2: construct.If(
                                                                lambda
                                                                ctx: ctx.payload_size == self.header_cmd2.sizeof(),
                                                                construct.Embed(self.header_cmd2))
                                                        },
                                                        default=construct.Pass
                                                        )
                                       )
        self.cmd_handlers = {
            0: self.cmd0,
            1: self.cmd1,
            2: self.cmd2
        }
        self.cmd0_handlers = {
            5: {6: self.cmd0_5_6},
        }

    # noinspection PyUnusedLocal
    def cmd0_5_6(self, h, packet):
        r = '\x02\x00\x00\x00\x10\x03\x11\x00\x7e\x01\x02\x38\x00\x09\x05\x06\x00\x00\x03\x04\x1f\x00\x00\x40\x00\x57' \
            '\x69\x69\x55\x34\x30\x66\x34\x30\x37\x38\x33\x39\x32\x35\x63\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x10\x00\x80\x03\x39\x62\x64\x62\x31\x38\x37\x31\x30\x39\x64\x64\x62\x36\x35\x33\x65' \
            '\x30\x62\x39\x64\x36\x32\x36\x65\x36\x34\x35\x35\x62\x37\x39\x31\x32\x61\x34\x38\x38\x35\x30\x33\x35\x34' \
            '\x30\x66\x34\x34\x61\x62\x62\x64\x63\x32\x65\x33\x39\x38\x36\x32\x32\x62\x31\x39\x63\x40\x51\x32\x00\x02' \
            '\x06\x2a\xb1\x16\x06\x57\x65\x67\x27\xd3\xd4\x57\xc5\x99\xd9\x2d\x2a\xa5\xc0\x3b\xe2\x40\xf4\x07\x83\x92' \
            '\x5c\xba\xbe\x01\x0e\x1e\x30\x04\x3e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x03\x1c\x3d\x8b\x5c\x35\x01\x0e\x1e' \
            '\x15\xab\x48\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x31\xe1\x04\xff\xa0\x98\xbc\xff' \
            '\xc0\xff\xb1\x00\xe8\x1f\x68\x1f\x90\x1f\x55\x07\xb0\xff\xff\x8a\xff\xff\x8d\x00\x00\x7d\x58\x02\x77\x55' \
            '\x02\x1e\x57\x02\xc8\xd9\x4c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x35' \
            '\x00\x1e\x00\x22\x03\xc3\x01\x50\x01\x61\x0e\xa1\x0e\x97\x01\xea\x9e\xe4\x17\x03\xa0\xb5\x43\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8b\x5c\x35\x01\x0e\x1e\x15\xab' \
            '\x48\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x31\xe1\x04\xff\xa0\x98\xbc\xff\xc0\xff' \
            '\xb1\x00\xe8\x1f\x68\x1f\x90\x1f\x55\x07\xb0\xff\xff\x8a\xff\xff\x8d\x00\x00\x7d\x58\x02\x77\x55\x02\x1e' \
            '\x57\x02\xc8\xd9\x4c\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x35\x00\x1e' \
            '\x00\x22\x03\xc3\x01\x50\x01\x61\x0e\xa1\x0e\x97\x01\xea\x9e\xe4\x17\x03\xa0\xb5\x43\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x05\x2a\x58\x00\x87\x0f\x00\x87\x0f\x01\x0e\x1e\x00' \
            '\x00\x00\x00\x00\x19\x00\x16\x1d\x6f\xbc\xff\xc0\xff\xb1\x00\xe8\x1f\x68\x1f\x90\x1f\x55\x07\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x35\x00\x1e\x00\x22\x03\xc3\x01\x50\x01\x61\x0e\xa1\x0e\x97\x01\xea\x9e\x00\x00' \
            '\x00\x13\x3b\x21\x00\x00\x00\x03\xba\x31\xe4\x17\x03\xa0\xb5\x43\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x87\x0f\x15\x01\x2d\x01\x4d\x01\x7a\x01\xb7\x01\xff\x01\x03\x26\x8c\x04\xa3\x49\x30\x30\x30' \
            '\x30\x30\x30\x30\x30\x30\x30\x73\x8f\x00\x87\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
            '\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\xa3\x49'[20:]
        self.send_response_cmd0(h, r)

    def cmd0(self, h, packet):
        print 'CMD0:%i:%i' % (h.id_primary, h.id_secondary)
        if h.id_primary not in self.cmd0_handlers or h.id_secondary not in self.cmd0_handlers[h.id_primary]:
            print 'unhandled', packet.encode('hex')
            return
        self.cmd0_handlers[h.id_primary][h.id_secondary](h, packet)

    def cmd1(self, h, packet):
        #print 'CMD1', packet[8:].encode('hex')
        self.send_response(h, '\x00\x16\x00\x19\x9e\x00\x00\x00\x40\x00\x40\x00\x00\x00\x01\xff')

    # noinspection PyUnusedLocal
    def cmd2(self, h, packet):
        print 'TIME base {:04x} seconds {:08x}'.format(h.JDN_base, h.seconds)
        self.send_response(h)

    def ack(self, h):
        ack = self.header.build(
            construct.Container(
                packet_type=self.PT_REQ_ACK if h.packet_type == self.PT_REQ else self.PT_RESP_ACK,
                cmd_id=h.cmd_id,
                payload_size=0,
                seq_id=h.seq_id
            )
        )
        WII_CMD_S.sendto(ack, ('192.168.1.10', WII_PORT_CMD))

    def send_request(self, h, data=''):
        self.send_cmd(h, self.PT_REQ, data)

    def send_response(self, h, data=''):
        self.send_cmd(h, self.PT_RESP, data)

    def send_response_cmd0(self, h, data='', result=CMD0_OK):
        assert h.cmd_id == 0
        h.flags = ((h.flags >> 3) & 0xfc) | 1
        h.error_code = result
        h.payload_size_cmd0 = len(data)
        self.send_response(h, data)

    def send_cmd(self, h, packet_type, data):
        h.packet_type = packet_type
        h.payload_size = len(data)
        # compensate for the fact that data doesn't include cmd0 header
        if h.cmd_id == 0:
            h.payload_size += self.header_cmd0.sizeof()
        WII_CMD_S.sendto(self.header.build(h) + data, ('192.168.1.10', WII_PORT_CMD))

    def update(self, packet):
        h = self.header.parse(packet)
        # don't track acks from the console for now
        if h.packet_type in (self.PT_REQ, self.PT_RESP):
            # print 'CMD', packet.encode('hex')
            self.ack(h)
            self.cmd_handlers[h.cmd_id](h, packet)


class ServiceMSG(ServiceBase):
    @staticmethod
    def update(packet):
        print 'MSG', packet.encode('hex')


class ServiceNOP(ServiceBase):
    def update(self, packet):
        pass


def init(wii_cmd_s, wii_port_cmd, wii_msg_s, wii_port_msg):
    global WII_CMD_S, WII_PORT_CMD, WII_MSG_S, WII_PORT_MSG
    WII_CMD_S = wii_cmd_s
    WII_PORT_CMD = wii_port_cmd
    WII_MSG_S = wii_msg_s
    WII_PORT_MSG = wii_port_msg
