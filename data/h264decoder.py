from cffi import FFI
import pygame

# TODO static alloc in_data and make interface for reading/writing directly to it
#   remove array.array usage of calling code


class H264Decoder:
    def __init_ffi(self):
        self.ffi = FFI()
        self.ffi.cdef('''
            // AVCODEC
            
            enum PixelFormat { PIX_FMT_YUV420P, PIX_FMT_RGB24, ... };
            
            void avcodec_register_all(void);
            
            struct AVPacket { ...; uint8_t *data; int size; ...; };
            void av_init_packet(struct AVPacket *pkt);
            
            enum AVCodecID { CODEC_ID_H264, ... };
            struct AVCodec *avcodec_find_decoder(enum AVCodecID id);

            struct AVCodecContext *avcodec_alloc_context3(struct AVCodec *codec);
            
            int avcodec_open2(struct AVCodecContext *avctx, struct AVCodec *codec,
                            struct AVDictionary **options);
            
            struct AVFrame { uint8_t *data[8]; int linesize[8]; ...; int key_frame; ...; };
            struct AVFrame *avcodec_alloc_frame(void);
            
            int avcodec_decode_video2(struct AVCodecContext *avctx, struct AVFrame *picture,
                                    int *got_picture_ptr, struct AVPacket *avpkt);
            
            int avcodec_close(struct AVCodecContext *avctx);
            
            void av_free(void *ptr);
            
            int avpicture_get_size(enum PixelFormat pix_fmt, int width, int height);
            
            int avpicture_fill(struct AVPicture *picture, uint8_t *ptr,
                            int pix_fmt, int width, int height);
            
            // SWSCALE
            
            #define SWS_BILINEAR ...
            #define SWS_FAST_BILINEAR ...
            struct SwsContext *sws_getContext(int srcW, int srcH, enum PixelFormat srcFormat,
                                            int dstW, int dstH, enum PixelFormat dstFormat,
                                            int flags, struct SwsFilter *srcFilter,
                                            struct SwsFilter *dstFilter, const double *param);
            
            int sws_scale(struct SwsContext *c, const uint8_t *const srcSlice[],
                        const int srcStride[], int srcSliceY,
                        int srcSliceH, uint8_t *const dst[],
                        const int dstStride[]);
            
            void sws_freeContext(struct SwsContext *c);
        ''')
        self.ns = self.ffi.verify(source='''
            #include <libavcodec/avcodec.h>
            #include <libswscale/swscale.h>
            ''', libraries=['avcodec', 'swscale'])

    def __init_avcodec(self):
        self.ns.avcodec_register_all()

        self.av_packet = self.ffi.new('struct AVPacket *')
        self.ns.av_init_packet(self.av_packet)

        self.codec = self.ns.avcodec_find_decoder(self.ns.CODEC_ID_H264)
        if not self.codec:
            raise Exception('avcodec_alloc_context3')
        self.context = self.ns.avcodec_alloc_context3(self.codec)
        if not self.context:
            raise Exception('avcodec_alloc_context3')
        if self.ns.avcodec_open2(self.context, self.codec, self.ffi.NULL) < 0:
            raise Exception('avcodec_open2')
        self.frame = self.ns.avcodec_alloc_frame()
        if not self.frame:
            raise Exception('avcodec_alloc_frame')
        self.got_frame = self.ffi.new('int *')
        self.out_frame = self.ns.avcodec_alloc_frame()

    def __init__(self, (in_x, in_y), (out_x, out_y)):
        self.in_x, self.in_y, self.out_x, self.out_y, self.out_buffer, self.sws_context = \
            in_x, in_y, out_y, out_x, None, None
        self.__init_ffi()
        self.__init_avcodec()
        self.update_dimensions((in_x, in_y), (out_x, out_y))

    def close(self):
        self.ns.sws_freeContext(self.sws_context)
        self.ns.av_free(self.out_frame)
        
        self.ns.avcodec_close(self.context)
        self.ns.av_free(self.context)
        self.ns.av_free(self.frame)

    def update_dimensions(self, (in_x, in_y), (out_x, out_y)):
        self.in_x, self.in_y = in_x, in_y
        self.out_x, self.out_y = out_x, out_y
        
        if self.sws_context is not None:
            self.ns.sws_freeContext(self.sws_context)
        self.sws_context = self.ns.sws_getContext(
            self.in_x, self.in_y, self.ns.PIX_FMT_YUV420P,
            self.out_x, self.out_y, self.ns.PIX_FMT_RGB24,
            self.ns.SWS_FAST_BILINEAR,
            self.ffi.NULL,
            self.ffi.NULL, self.ffi.NULL)
        
        bytes_req = self.ns.avpicture_get_size(self.ns.PIX_FMT_RGB24, self.out_x, self.out_y)
        self.out_buffer = self.ffi.new('uint8_t [%i]' % bytes_req)
        self.ns.avpicture_fill(
            self.ffi.cast('struct AVPicture *', self.out_frame),
            self.out_buffer,
            self.ns.PIX_FMT_RGB24,
            self.out_x, self.out_y)

    def display_frame(self, encoded_nalu):
        in_data = self.ffi.new('uint8_t []', encoded_nalu)
        self.av_packet.data = in_data
        self.av_packet.size = len(encoded_nalu)
        
        length = self.ns.avcodec_decode_video2(self.context, self.frame, self.got_frame, self.av_packet)
        if length < 0:
            raise Exception('avcodec_decode_video2')
        elif length != self.av_packet.size:
            raise Exception('expected to decode a single complete frame')
        elif self.got_frame[0]:
            # print 'keyframe:', s.frame.key_frame
            # convert from YUV to RGB
            self.ns.sws_scale(
                self.sws_context,
                self.frame.data, self.frame.linesize,
                0, self.in_y,
                self.out_frame.data, self.out_frame.linesize)

            surface = pygame.image.frombuffer(
                self.ffi.buffer(self.out_frame.data[0], self.out_frame.linesize[0] * self.out_y),
                (self.out_x, self.out_y),
                'RGB')
            pygame.display.get_surface().blit(surface, (0, 0))
            pygame.display.flip()
