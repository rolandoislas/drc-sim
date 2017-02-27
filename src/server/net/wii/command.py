import construct

from src.server.data.args import Args
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
        # Returns the 4 byte UIC firmware version followed by the first 768 bytes of the UIC EEPROM.
        # Send null data TODO get updated firmware
        r = '\x00' * 772
        self.send_response_cmd0(h, r)

    def cmd0(self, h, packet):
        if Args.args.debug:
            print 'CMD0:%i:%i' % (h.id_primary, h.id_secondary)
        if h.id_primary not in self.cmd0_handlers or h.id_secondary not in self.cmd0_handlers[h.id_primary]:
            if Args.args.debug:
                print 'unhandled', packet.encode('hex')
            return
        self.cmd0_handlers[h.id_primary][h.id_secondary](h, packet)

    # noinspection PyUnusedLocal
    def cmd1(self, h, packet):
        if Args.args.debug:
            print 'CMD1', packet[8:].encode('hex')
        r = '\x00' * 16
        self.send_response(h, r)

    # noinspection PyUnusedLocal
    def cmd2(self, h, packet):
        if Args.args.debug:
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
