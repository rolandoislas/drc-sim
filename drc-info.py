import select
import socket
import time
from threading import Thread

from src.server.data import constants

sock_cmd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_cmd.bind(("192.168.1.10", constants.PORT_WII_CMD))
sock_msg = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_msg.bind(("192.168.1.10", constants.PORT_WII_MSG))
sock_hid = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_hid.bind(("192.168.1.10", constants.PORT_WII_HID))
sock_vid = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_vid.bind(("192.168.1.10", constants.PORT_WII_VID))
sock_aud = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_aud.bind(("192.168.1.10", constants.PORT_WII_AUD))


def print_packet(s, name, do_print=True):
    data = s.recv(2048)
    if do_print:
        print "%s: %s" % (name, data.encode('hex'))


def send_cmd(data):
    sock_cmd.sendto(data, ("192.168.1.11", constants.PORT_WII_CMD + 100))


def cmd_request():
    sid = 0
    while True:
        data = {
            0: {0: {0: "000000000c00%s087e0115880040000000000000",
                    10: "000000000d00%s007e0101780040000a0000000100"},
                4: {4: "000000000c00%s007e0109780040040400000000"},
                5: {6: "000000000c00%s007e0101a80040050600000000",
                    12: "000000001100%s007e0102f80040050c000000050e0300870f",
                    24: "000000001600%s007e0101c8004005180000000a54313936333030303030"}
                },
            1: {0: {0: "000001003000%s1a010000000000000000000000803e000000010002000000000000000070000000404003002d00000"
                       "10000000000000000"  # Just CMD 1 - keys 0 0 are there so it fits nicely with the for loop
                    }
                }
        }
        for command in data.keys():
            for primary_id in data[command].keys():
                for secondary_id in data[command][primary_id].keys():
                    h = hex(sid).replace("0x", "")
                    if len(h) == 1:
                        h = "0" + h
                    send_data = bytes((data[command][primary_id][secondary_id] % h).decode("hex"))
                    print "Sending command %d %d %d" % (command, primary_id, secondary_id)
                    send_cmd(send_data)
                    sid += 1
                    time.sleep(1)


if __name__ == '__main__':
    Thread(target=cmd_request).start()

    while True:
        rlist, wlist, xlist = select.select((sock_cmd, sock_msg, sock_hid, sock_vid, sock_aud), (), (), 1)
        if rlist:
            for s in rlist:
                if s == sock_hid:
                    print_packet(s, "hid", False)
                    pass
                elif s == sock_aud:
                    print_packet(s, "aud")
                elif s == sock_vid:
                    print_packet(s, "vid")
                elif s == sock_cmd:
                    print_packet(s, "cmd")
                elif s == sock_msg:
                    print_packet(s, "msg")
