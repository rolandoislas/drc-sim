import construct

from src.common.data import constants
from src.server.net import sockets


class CommandHandler:
    PT_REQ = 0
    PT_REQ_ACK = 1
    PT_RESP = 2
    PT_RESP_ACK = 3

    CMD0_OK = 0

    def __init__(self):
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

    # noinspection PyUnusedLocal
    def cmd1(self, h, packet):
        # print 'CMD1', packet[8:].encode('hex')
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
        sockets.Sockets.WII_CMD_S.sendto(ack, ('192.168.1.10', constants.PORT_WII_CMD))

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
        sockets.Sockets.WII_CMD_S.sendto(self.header.build(h) + data, ('192.168.1.10', constants.PORT_WII_CMD))

    def update(self, packet):
        h = self.header.parse(packet)
        # don't track acks from the console for now
        if h.packet_type in (self.PT_REQ, self.PT_RESP):
            # print 'CMD', packet.encode('hex')
            self.ack(h)
            self.cmd_handlers[h.cmd_id](h, packet)

    def close(self):
        pass
