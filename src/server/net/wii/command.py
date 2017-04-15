import ast
import codecs

import construct

from src.server.data import constants
from src.server.data.resource import Resource
from src.server.data.struct import command
from src.server.net import sockets
from src.server.util.logging.logger_backend import LoggerBackend


class CommandHandler:
    PT_REQ = 0
    PT_REQ_ACK = 1
    PT_RESP = 2
    PT_RESP_ACK = 3

    CMD0_OK = 0

    def __init__(self):
        self.cmd_handlers = {
            0: self.cmd0,
            1: self.cmd1,
            2: self.cmd2
        }
        self.command_responses = {}
        self.set_region()

    def set_region(self, region=None):
        # Empty command data
        if not region or region.upper() == "NONE":
            self.command_responses = ast.literal_eval(Resource("command/na.json").resource)
            for response in self.command_responses.keys():
                if isinstance(self.command_responses[response], str):
                    self.command_responses[response] = "0" * len(self.command_responses[response])
                else:
                    for id_primary in self.command_responses[response].keys():
                        for id_secondary in self.command_responses[response][id_primary].keys():
                            self.command_responses[response][id_primary][id_secondary] = \
                                "0" * len(self.command_responses[response][id_primary][id_secondary])
        # Region specific command data
        else:
            self.command_responses = ast.literal_eval(Resource("command/%s.json" % region.lower()).resource)

    def cmd0(self, h):
        id_primary = str(h.id_primary)
        id_secondary = str(h.id_secondary)
        LoggerBackend.debug('CMD0:%s:%s' % (id_primary, id_secondary))
        if id_primary not in self.command_responses["0"] or id_secondary not in self.command_responses["0"][id_primary]:
            LoggerBackend.debug('unhandled CMD0 %s %s', id_primary, id_secondary)
            return
        response = self.command_responses["0"][id_primary][id_secondary]
        response = codecs.decode(response[40:], "hex")
        self.send_response_cmd0(h, response)

    def cmd1(self, h):
        response = self.command_responses["1"]
        response = codecs.decode(response[16:], "hex")
        self.send_response(h, response)

    def cmd2(self, h):
        LoggerBackend.extra('TIME base {:04x} seconds {:08x}'.format(h.JDN_base, h.seconds))
        self.send_response(h)

    def ack(self, h):
        ack = command.header.build(
            construct.Container(
                packet_type=self.PT_REQ_ACK if h.packet_type == self.PT_REQ else self.PT_RESP_ACK,
                cmd_id=h.cmd_id,
                payload_size=0,
                seq_id=h.seq_id
            )
        )
        sockets.Sockets.WII_CMD_S.sendto(ack, ('192.168.1.10', constants.PORT_WII_CMD))

    def send_request(self, h, data=b''):
        self.send_cmd(h, self.PT_REQ, data)

    def send_response(self, h, data=b''):
        self.send_cmd(h, self.PT_RESP, data)

    def send_response_cmd0(self, h, data=b'', result=CMD0_OK):
        assert h.cmd_id == 0
        h.flags = ((h.flags >> 3) & 0xfc) | 1
        h.error_code = result
        h.payload_size_cmd0 = len(data)
        self.send_response(h, data)

    @staticmethod
    def send_cmd(h, packet_type, data):
        h.packet_type = packet_type
        h.payload_size = len(data)
        # compensate for the fact that data doesn't include cmd0 header
        if h.cmd_id == 0:
            h.payload_size += command.header_cmd0.sizeof()
        sockets.Sockets.WII_CMD_S.sendto(command.header.build(h) + data, ('192.168.1.10', constants.PORT_WII_CMD))

    def update(self, packet):
        h = command.header.parse(packet)
        # don't track acks from the console for now
        if h.packet_type in (self.PT_REQ, self.PT_RESP):
            LoggerBackend.finer('CMD (%d): %s', h.cmd_id, codecs.encode(packet, "hex").decode())
            LoggerBackend.finer(h)
            self.ack(h)
            self.cmd_handlers[h.cmd_id](h)

    def close(self):
        pass
