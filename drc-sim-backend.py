import construct
import pyaudio
import select
import socket
import array
import pygame
from H264Decoder import H264Decoder
from control import controller

pygame.init()
pygame.display.set_mode([854, 480], pygame.RESIZABLE)
pygame.display.set_caption("drc-sim")
done = False
clock = pygame.time.Clock()


def service_addend(ip):
    if int(ip.split('.')[3]) == 10:
        return 0
    else:
        return 100


def udp_service(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port + service_addend(ip)))
    return sock


WII_PORT_MSG = 50010
WII_PORT_VID = 50020
WII_PORT_AUD = 50021
WII_PORT_HID = 50022
WII_PORT_CMD = 50023
SERVER_PORT_VID = 50000
SERVER_PORT_AUD = 50001
SERVER_PORT_CMD = 50002

# hack for now, replace with dhcp result
WII_LOCAL_IP = '192.168.1.11'
SERVER_IP = '0.0.0.0'

WII_MSG_S = udp_service(WII_LOCAL_IP, WII_PORT_MSG)
WII_VID_S = udp_service(WII_LOCAL_IP, WII_PORT_VID)
WII_AUD_S = udp_service(WII_LOCAL_IP, WII_PORT_AUD)
WII_HID_S = udp_service(WII_LOCAL_IP, WII_PORT_HID)
WII_CMD_S = udp_service(WII_LOCAL_IP, WII_PORT_CMD)


def server(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip, port))
    sock.listen(5)
    return sock

SERVER_VID_S = server(SERVER_IP, SERVER_PORT_VID)
SERVER_CMD_S = server(SERVER_IP, SERVER_PORT_CMD)


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
        self.p = pyaudio.PyAudio()
        self.stream = None

        self.pa_num_bufs = 15
        self.pa_ring = [array.array('H', '\0' * 416 * 2)] * self.pa_num_bufs
        self.pa_wpos = self.pa_rpos = 0

    def close(self):
        if self.stream is not None:
            # hangs the process, dunno why
            # s.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.p is not None:
            self.p.terminate()
            self.p = None
        self.is_streaming = False

    # noinspection PyUnusedLocal
    def __pa_callback(self, in_data, frame_count, time_info, status):
        samples = self.pa_ring[self.pa_wpos]
        self.pa_wpos += 1
        self.pa_wpos %= self.pa_num_bufs
        samples.extend(self.pa_ring[self.pa_wpos])
        self.pa_wpos += 1
        self.pa_wpos %= self.pa_num_bufs
        return samples, pyaudio.paContinue

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

            if self.is_streaming and not self.stream.is_active():
                self.stream.close()
                self.is_streaming = False

            if not self.is_streaming:
                self.stream = self.p.open(format=pyaudio.paInt16,
                                          channels=2,
                                          rate=48000,
                                          output=True,
                                          frames_per_buffer=416 * 2,
                                          stream_callback=self.__pa_callback)
                self.stream.start_stream()
                self.is_streaming = True


class ServiceVSTRM(ServiceBase):
    dimensions = {
        'camera': (640, 480),
        'gamepad': (854, 480)
    }

    def __init__(self):
        super(ServiceVSTRM, self).__init__()
        self.decoder = H264Decoder(
            self.dimensions['gamepad'],
            pygame.display.get_surface().get_size())
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
            # update surface
            nals = self.h264_nal_encapsulate(is_idr, self.frame)
            self.decoder.display_frame(nals.tostring())
            # output fps
            clock.tick()
            pygame.display.set_caption("drc-sim - fps: " + str(round(clock.get_fps())))

    # noinspection PyUnusedLocal
    def resize_output(self, (x, y)):
        d = self.dimensions['gamepad']
        fit = pygame.Rect((0, 0), d).fit(pygame.display.get_surface().get_rect())
        self.decoder.update_dimensions(d, fit.size)


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
        print 'CMD1', packet[8:].encode('hex')
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


class ServiceIMGSTRM(ServiceBase):
    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def update(self, packet):
        # output surface image
        client, address = SERVER_VID_S.accept()
        image_buffer = pygame.image.tostring(pygame.display.get_surface(), "RGB", False)
        print address
        client.sendall(image_buffer)


class ServiceCNTRL(ServiceBase):
    def update(self, packet):
        pass


service_handlers = {
    WII_MSG_S: ServiceMSG(),
    WII_VID_S: ServiceVSTRM(),
    WII_AUD_S: ServiceASTRM(),
    WII_CMD_S: ServiceCMD(),
    SERVER_VID_S: ServiceIMGSTRM(),
    SERVER_CMD_S: ServiceCNTRL()
}

hid_seq_id = 0


def hid_snd():
    global hid_seq_id

    report = array.array('H', '\0\0' * 0x40)

    # 16bit LE @ 0 seq_id
    # seems to be ignored
    report[0] = hid_seq_id
    # 16bit @ 2
    button_bits = 0
    # Get input
    button_bits |= controller.get_input()
    report[40] |= controller.get_l3_r3_input()

    # 16bit LE array @ 6
    # LX, LY, RX, RY
    # 0: l stick l/r
    # 1: l stick u/d
    # 2: l trigger
    # 3: r stick l/r
    # 4: r stick u/d
    # 5: r trigger
    def scale_stick(old_value, old_min, old_max, new_min, new_max):
        return int((((old_value - old_min) * (new_max - new_min)) / (old_max - old_min)) + new_min)

    for i in xrange(6):
        if i not in (2, 5):
            orig = 0
            scaled = 0x800
            if abs(orig) > 0.2:
                if i in (0, 3):
                    scaled = scale_stick(orig, -1, 1, 900, 3200)
                elif i in (1, 4):
                    scaled = scale_stick(orig, 1, -1, 900, 3200)
            # print '%04i %04i %f' % (i, scaled, orig)
            stick_mapping = {0: 0, 1: 1, 3: 2, 4: 3}
            report[3 + stick_mapping[i]] = scaled
    report[1] = (button_bits >> 8) | ((button_bits & 0xff) << 8)

    # touchpanel crap @ 36 - 76
    # byte_18 = 0
    byte_17 = 3
    # byte_9b8 = 0
    byte_9fd = 6
    umi_fw_rev = 0x40
    # byte_9fb = 0
    byte_19 = 2
    if pygame.mouse.get_pressed()[0]:
        point = pygame.mouse.get_pos()
        screen_x, screen_y = pygame.display.get_surface().get_size()
        x = scale_stick(point[0], 0, screen_x, 200, 3800)
        y = scale_stick(point[1], 0, screen_y, 200, 3800)
        z1 = 2000

        for i in xrange(10):
            report[18 + i * 2 + 0] = 0x80 | x
            report[18 + i * 2 + 1] = 0x80 | y

        report[18 + 0 * 2 + 0] |= ((z1 >> 0) & 7) << 12
        report[18 + 0 * 2 + 1] |= ((z1 >> 3) & 7) << 12
        report[18 + 1 * 2 + 0] |= ((z1 >> 6) & 7) << 12
        report[18 + 1 * 2 + 1] |= ((z1 >> 9) & 7) << 12

    report[18 + 3 * 2 + 1] |= ((byte_17 >> 0) & 7) << 12
    report[18 + 4 * 2 + 0] |= ((byte_17 >> 3) & 7) << 12
    report[18 + 4 * 2 + 1] |= ((byte_17 >> 6) & 3) << 12

    report[18 + 5 * 2 + 0] |= ((byte_9fd >> 0) & 7) << 12
    report[18 + 5 * 2 + 1] |= ((byte_9fd >> 3) & 7) << 12
    report[18 + 6 * 2 + 0] |= ((byte_9fd >> 6) & 3) << 12

    report[18 + 7 * 2 + 0] |= ((umi_fw_rev >> 4) & 7) << 12

    # TODO checkout what's up with | 4
    report[18 + 9 * 2 + 1] |= ((byte_19 & 2) | 4) << 12

    # 8bit @ 80

    report[0x3f] = 0xe000
    # print report.tostring().encode('hex')
    WII_HID_S.sendto(report, ('192.168.1.10', WII_PORT_HID))
    # hid_seq_id += 1


EVT_SEND_HID = pygame.USEREVENT
pygame.time.set_timer(EVT_SEND_HID, int((1. / 180.) * 1000.))


def loop():
    global done
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        elif event.type == pygame.VIDEORESIZE:
            pygame.display.set_mode(event.size, pygame.RESIZABLE)
            service_handlers[WII_VID_S].resize_output(event.size)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSLASH:
                WII_MSG_S.sendto('\1\0\0\0', ('192.168.1.10', WII_PORT_MSG))
        elif event.type == EVT_SEND_HID:
            hid_snd()

    rlist, wlist, xlist = select.select(service_handlers.keys(), (), (), 1)

    if not rlist:
        return
    for sock in rlist:
        try:
            data = sock.recvfrom(2048)[0]
        except socket.error:
            data = sock
        service_handlers[sock].update(data)

while not done:
    loop()

for s in service_handlers.itervalues():
    s.close()

pygame.quit()
