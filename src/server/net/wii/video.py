import array
from PIL import Image
from io import BytesIO

import construct
import lz4

import time

from src.common.data import constants
from src.common.data.config import Config
from src.server.data.config import Config, ConfigServer
from src.server.data.h264decoder import H264Decoder
from src.server.net.server.video import ServiceVID
from src.server.net.sockets import Sockets
from src.server.net.wii.base import ServiceBase


class VideoHandler(ServiceBase):
    def __init__(self):
        super(VideoHandler, self).__init__()
        self.last_sent_time = 0
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
                    Sockets.WII_MSG_S.sendto('\1\0\0\0', ('192.168.1.10', constants.PORT_WII_MSG))
                    return

        self.frame.fromstring(packet[16:])

        if self.is_streaming and h.frame_end:
            # Get image
            nals = self.h264_nal_encapsulate(is_idr, self.frame)
            image_buffer = self.decoder.get_image_buffer(nals.tostring())
            # Check fps limit
            if ConfigServer.fps < 60 and time.time() - self.last_sent_time < 1. / ConfigServer.fps:
                return
            # Reduce quality at the expense of CPU
            if ConfigServer.quality < 100:
                image = Image.frombuffer("RGB", (constants.WII_VIDEO_WIDTH, constants.WII_CAMERA_HEIGHT), image_buffer,
                                         "raw", "RGB", 0, 1)
                ib = BytesIO()
                image.save(ib, "JPEG", quality=ConfigServer.quality)
                ServiceVID.broadcast(ib.getvalue())
            else:
                ServiceVID.broadcast(image_buffer)
            # Update time
            self.last_sent_time = time.time()
