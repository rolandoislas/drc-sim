import construct
import pyaudio
import select
import socket
import array
import pygame
import time
from H264Decoder import H264Decoder

pygame.init()
pygame.display.set_mode([854, 480])
pygame.display.set_caption("drc-sim")
done = False
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

def service_addend(ip):
    if int(ip.split('.')[3]) == 10:
        return 0
    else:
        return 100

def udp_service(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port + service_addend(ip)))
    return sock

PORT_MSG = 50010
PORT_VID = 50020
PORT_AUD = 50021
PORT_HID = 50022
PORT_CMD = 50023

# hack for now, replace with dhcp result
LOCAL_IP = '192.168.1.11'

MSG_S = udp_service(LOCAL_IP, PORT_MSG)
VID_S = udp_service(LOCAL_IP, PORT_VID)
AUD_S = udp_service(LOCAL_IP, PORT_AUD)
HID_S = udp_service(LOCAL_IP, PORT_HID)
CMD_S = udp_service(LOCAL_IP, PORT_CMD)

class ServiceBase(object):
    def __init__(s):
        s.seq_id_expect = None

    def update_seq_id(s, seq_id):
        ret = True
        if s.seq_id_expect == None: s.seq_id_expect = seq_id
        elif s.seq_id_expect != seq_id:
            ret = False
        s.seq_id_expect = (seq_id + 1) & 0x3ff
        return ret

pa_initted = False
pa_num_bufs = 9
pa_ring = [array.array('H', '\0' * 416)] * pa_num_bufs
pa_wpos = pa_rpos = 0
def pa_callback(in_data, frame_count, time_info, status):
    global pa_num_bufs, pa_ring, pa_wpos, pa_rpos
    samples = pa_ring[pa_wpos]
    pa_wpos += 1
    pa_wpos %= pa_num_bufs
    samples.extend(pa_ring[pa_wpos])
    pa_wpos += 1
    pa_wpos %= pa_num_bufs
    return (samples, pyaudio.paContinue)

class ServiceASTRM(ServiceBase):
    def __init__(s):
        super(ServiceASTRM, s).__init__()
        s.header_base = construct.BitStruct('ASTRMBaseHeader',
            construct.BitField('fmt', 3),
            construct.Bit('channel'),
            construct.Flag('vibrate'),
            construct.Bit('packet_type'),
            construct.BitField('seq_id', 10),
            construct.BitField('payload_size', 16)
        )
        s.header_aud = construct.Struct('ASTRMAudioHeader',
            construct.ULInt32('timestamp'),
        #    construct.Array(lambda ctx: ctx.payload_size, construct.UBInt8("data"))
        )
        s.header_msg = construct.Struct('ASTRMMsgHeader',
            # This is kind of a hack, (there are two timestamp fields, which one is used depends on packet_type
            construct.ULInt32('timestamp_audio'),
            construct.ULInt32('timestamp'),
            construct.Array(2, construct.ULInt32('freq_0')), # -> mc_video
            construct.Array(2, construct.ULInt32('freq_1')), # -> mc_sync
            construct.ULInt8('vid_format'),
            construct.Padding(3)
        )
        s.header = construct.Struct('ASTRMHeader',
            construct.Embed(s.header_base),
            construct.Switch('format_hdr', lambda ctx: ctx.packet_type,
                {
                    0 : construct.Embed(s.header_aud),
                    1 : construct.Embed(s.header_msg),
                },
                default = construct.Pass
            )
        )

    def update(s, packet):
        global pa_ring, pa_initted, pa_rpos
        h = s.header.parse(packet)
        
        # ignore vid_format packets for now
        if h.packet_type == 0:
            seq_ok = s.update_seq_id(h.seq_id)
            if not seq_ok:
                print 'astrm bad seq_id'
            if h.fmt != 1 or h.channel != 0:
                raise Exception('astrm currently only handles 48kHz PCM stereo')
            if len(packet) != 8 + h.payload_size:
                raise Exception('astrm bad payload_size')
            
            if h.vibrate:
                print '*vibrate*'
            
            pa_ring[pa_rpos] = array.array('H', packet[8:])
            pa_rpos += 1
            pa_rpos %= pa_num_bufs
            
            if pa_rpos > 4 and pa_initted == False:
                p = pyaudio.PyAudio()
                stream = p.open(format = pyaudio.paInt16,
                    channels = 2,
                    rate = 48000,
                    output = True,
                    frames_per_buffer = 416 * 2,
                    stream_callback = pa_callback)
                pa_initted = True

class ServiceVSTRM(ServiceBase):
    dimensions = {
        'camera' : (640, 480),
        'gamepad' :  (854, 480)
    }
    
    def __init__(s):
        super(ServiceVSTRM, s).__init__()
        s.decoder = H264Decoder(
            s.dimensions['gamepad'],
            pygame.display.get_surface().get_size())
        s.header = construct.BitStruct('VSTRMHeader',
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
        s.frame = array.array('B')
        s.is_streaming = False
        s.frame_decode_num = 0

    def packet_is_idr(s, packet):
        return packet[8:16].find('\x80') != -1

    def h264_nal_encapsulate(s, is_idr, vstrm):
        slice_header = 0x25b804ff if is_idr else (0x21e003ff | ((s.frame_decode_num & 0xff) << 13))
        s.frame_decode_num += 1
        
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
                     (slice_header >>  8) & 0xff,
                      slice_header & 0xff])
        
        # add escape codes
        nals.extend(vstrm[:2])
        for i in xrange(2, len(vstrm)):
            if vstrm[i] <= 3 and nals[-2] == 0 and nals[-1] == 0:
                nals.extend([3])
            nals.extend([vstrm[i]])
        
        return nals

    def update(s, packet):
        h = s.header.parse(packet)
        is_idr = s.packet_is_idr(packet)
        
        seq_ok = s.update_seq_id(h.seq_id)
        
        if not seq_ok:
            s.is_streaming = False
        
        if h.frame_begin:
            s.frame = array.array('B')
            if s.is_streaming == False:
                if is_idr:
                    s.is_streaming = True
                else:
                    # request a new IDR frame
                    MSG_S.sendto('\1\0\0\0', ('192.168.1.10', PORT_MSG))
                    return
        
        s.frame.fromstring(packet[16:])
        
        if s.is_streaming and h.frame_end:
            nals = s.h264_nal_encapsulate(is_idr, s.frame)
            s.decoder.display_frame(nals.tostring())

class ServiceCMD(ServiceBase):
    PT_REQ      = 0
    PT_REQ_ACK  = 1
    PT_RESP     = 2
    PT_RESP_ACK = 3
    
    CMD0_OK = 0
    
    def __init__(s):
        s.header_cmd0 = construct.Struct('CMD0Header',
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
        '''
        s.header_cmd1 = construct.Struct('CMD1Header',
            
        )
        '''
        s.header_cmd2 = construct.Struct('CMD2Header',
            construct.ULInt16('JDN_base'),
            construct.Padding(2),
            construct.ULInt32('seconds')
        )
        s.header = construct.Struct('CMDHeader',
            construct.ULInt16('packet_type'),
            construct.ULInt16('cmd_id'),
            construct.ULInt16('payload_size'),
            construct.ULInt16('seq_id'),
            construct.Switch('cmd_hdr', lambda ctx: ctx.cmd_id,
                {
                    0 : construct.If(lambda ctx: ctx.payload_size >= s.header_cmd0.sizeof(), construct.Embed(s.header_cmd0)),
                    2 : construct.If(lambda ctx: ctx.payload_size == s.header_cmd2.sizeof(), construct.Embed(s.header_cmd2)),
                },
                default = construct.Pass
            )
        )
        s.cmd_handlers = {
            0 : s.cmd0,
            1 : s.cmd1,
            2 : s.cmd2
        }
        s.cmd0_handlers = {
            5 : { 6 : s.cmd0_5_6 },
        }

    def cmd0_5_6(s, packet):
        print 'CMD 0 5 6', packet[20:].encode('hex')
        s.send_response_cmd0(h,
            '')

    def cmd0(s, h, packet):
        s.cmd0_handlers[h.id_primary][h.id_secondary](packet)

    def cmd1(s, h, packet):
        pass

    def cmd2(s, h, packet):
        print 'TIME base {:04x} seconds {:08x}'.format(h.JDN_base, h.seconds)
        s.send_response(h)

    def ack(s, h):
        ack = s.header.build(
            construct.Container(
                packet_type = s.PT_REQ_ACK if h.packet_type == s.PT_REQ else s.PT_RESP_ACK,
                cmd_id = h.cmd_id,
                payload_size = 0,
                seq_id = h.seq_id
            )
        )
        CMD_S.sendto(ack, ('192.168.1.10', PORT_MSG))

    def send_request(s, h, data = ''):
        s.send_cmd(h, s.PT_REQ, data)

    def send_response(s, h, data = ''):
        s.send_cmd(h, s.PT_RESP, data)

    def send_response_cmd0(s, h, data = '', result = s.CMD0_OK):
        assert h.cmd_id == 0
        h.flags = ((h.flags >> 3) & 0xfc) | 1
        h.error_code = result
        h.payload_size_cmd0 = len(data)
        s.send_response(h, data)

    def send_cmd(s, h, type, data):
        h.packet_type = type
        h.payload_size = len(data)
        # compensate for the fact that data doesn't include cmd0 header
        if h.cmd_id == 0:
            h.payload_size += s.header_cmd0.sizeof()
        CMD_S.sendto(s.header.build(h) + data, ('192.168.1.10', PORT_MSG))

    def update(s, packet):
        #print 'CMD', packet.encode('hex')
        h = s.header.parse(packet)
        # don't track acks from the console for now
        if h.packet_type in (s.PT_REQ, s.PT_RESP):
            s.ack(h)
            s.cmd_handlers[h.cmd_id](h, packet)

class ServiceMSG(ServiceBase):
    def update(s, packet):
        print 'MSG', packet.encode('hex')

class ServiceNOP(ServiceBase):
    def update(s, packet):
        pass

service_handlers = {
    MSG_S : ServiceMSG(),
    VID_S : ServiceVSTRM(),
    AUD_S : ServiceASTRM(),
    CMD_S : ServiceCMD()
}

hid_seq_id = 0
def hid_snd():
    global joystick, hid_seq_id
    
    report = array.array('B', '\0' * 0x80)
    
    button_mapping = {
        0 : 0x8000, # a
        1 : 0x4000, # b
        2 : 0x2000, # x
        3 : 0x1000, # y
        4 : 0x0020, # l
        5 : 0x0010, # r
        6 : 0x0004, # back (minus)
        7 : 0x0008, # start (plus)
        8 : 0x0002, # xbox (home)
        # extra buttons
        9 : 0x08, # l3
       10 : 0x04  # r3
    }
    hat_mapping_x = {
        0 : 0x000,
       -1 : 0x800, # l
        1 : 0x400, # r
    }
    hat_mapping_y = {
        0 : 0x000,
       -1 : 0x100, # d
        1 : 0x200, # u
    }
    trigger_mapping = {
        2 : 0x0080, # l
        5 : 0x0040  # r
    }
    
    # 16bit LE @ 0 seq_id
    # seems to be ignored
    report[1] = (hid_seq_id >> 8) & 0xff
    report[0] = hid_seq_id & 0xff
    # 16bit @ 2
    button_bits = 0
    for i in xrange(9):
        if joystick.get_button(i):
            button_bits |= button_mapping[i]
    # hat: (<l/r>, <u/d>) [-1,1]
    hat = joystick.get_hat(0)
    button_bits |= hat_mapping_x[hat[0]]
    button_bits |= hat_mapping_y[hat[1]]
    # 16bit LE array @ 6
    # LX, LY, RX, RY
    # 0: l stick l/r
    # 1: l stick u/d
    # 2: l trigger
    # 3: r stick l/r
    # 4: r stick u/d
    # 5: r trigger
    def scale_stick(OldValue, OldMin, OldMax, NewMin, NewMax):
        return int((((OldValue - OldMin) * (NewMax - NewMin)) / (OldMax - OldMin)) + NewMin)
    for i in xrange(6):
        if i in (2, 5):
            if joystick.get_axis(i) > 0:
                button_bits |= trigger_mapping[i]
        else:
            orig = joystick.get_axis(i)
            scaled = 0x800
            if abs(orig) > 0.2:
                if i in (0, 3):
                    scaled = scale_stick(orig, -1, 1, 900, 3200)
                elif i in (1, 4):
                    scaled = scale_stick(orig, 1, -1, 900, 3200)
            #print '%04i %04i %f' % (i, scaled, orig)
            report[6 + i * 2 + 0] = scaled & 0xff
            report[6 + i * 2 + 1] = (scaled >> 8) & 0xff
    report[2] = (button_bits >> 8) & 0xff
    report[3] = button_bits & 0xff
    # 8bit @ 80
    for i in xrange(9,11):
        if joystick.get_button(i):
            report[80] |= button_mapping[i]
    
    report[0x7f] = 0xe0
    
    HID_S.sendto(report, ('192.168.1.10', PORT_HID))
    hid_seq_id += 1

EVT_SEND_HID = pygame.USEREVENT
pygame.time.set_timer(EVT_SEND_HID, int((1. / 180.) * 1000.))

while not done:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        elif event.type == EVT_SEND_HID:
            hid_snd()
    
    rlist, wlist, xlist = select.select(service_handlers.keys(), (), (), 100)
    
    if not rlist:
        continue
    
    for sock in rlist:
        service_handlers[sock].update(sock.recvfrom(2048)[0])

pygame.quit()