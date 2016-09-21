import pyaudio
import pygame
import socket
import sys
import time

from control import controller
from data import constants
from net.codec import Codec


class Frontend:
    def __init__(self):
        self.IP = ""
        self.VID_S, self.AUD_S, self.CMD_S = None, None, None
        self.SOCKET_HANDLERS = {}

        self.clock = pygame.time.Clock()
        self.input_time = 0
        self.audio_bytes = None
        self.fps = []
        self.video_stream_last_part = ""
        self.audio_stream_last_part = ""

        pygame.init()
        self.screen = pygame.display.set_mode((constants.WII_VIDEO_WIDTH, constants.WII_VIDEO_HEIGHT))
        pygame.display.set_caption("drc-sim")

        self.pya = pyaudio.PyAudio()
        self.pya_stream = self.pya.open(format=pyaudio.paInt16,
                                        channels=2,
                                        rate=48000,
                                        output=True,
                                        frames_per_buffer=416 * 2,
                                        stream_callback=self.pyaudio_callback)
        self.pya_stream.start_stream()

        self.connect()

    @staticmethod
    def client(ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        return sock

    def connect(self):
        try:
            self.CMD_S = self.client(self.IP, constants.SERVER_PORT_CMD)
            self.VID_S = self.client(self.IP, constants.SERVER_PORT_VID)
            self.AUD_S = self.client(self.IP, constants.SERVER_PORT_AUD)
            self.VID_S.setblocking(0)
            self.AUD_S.setblocking(0)
            self.CMD_S.setblocking(1)
        except socket.error:
            time.sleep(5)
            self.connect()

    @staticmethod
    def check_quit():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

    def get_data_from_sock(self, sock):
        data = ""
        size = 0
        bytes_received = 0
        while True:
            try:
                bytes_to_get = 4096 if size == 0 or size - bytes_received >= 4096 else size - bytes_received
                chunk = sock.recv(bytes_to_get)
            except socket.error, e:
                # no data (non blocking socket) TODO timeout check
                if e.errno == socket.errno.EAGAIN:
                    return ""
                raise e
            # get the size of the data
            if size == 0:
                try:
                    header_size, data_size = Codec.decode_packet_header(chunk)
                    size = header_size + data_size
                except ValueError:
                    raise IOError("missing packet data - skipping packet")
            bytes_received += len(chunk)
            # save the data chunks
            data += chunk
            # check if all data has been received
            if size == bytes_received:
                return bytes(Codec.decode(data))

    def update_video(self):
        try:
            image_buffer = self.get_data_from_sock(self.VID_S)
        except IOError, e:
            print "[Video]", e
            return
        if not image_buffer:
            return
        try:
            # Convert to image
            image = pygame.image.frombuffer(image_buffer, (854, 480), "RGB")
        except Exception, e:
            print e
        else:
            self.screen.blit(image, (0, 0))
            pygame.display.flip()
            # Update clock TODO get actual fps
            self.clock.tick()

    def get_average_fps(self):
        if len(self.fps) > 1000:
            self.fps = self.fps[1:]
        self.fps.append(self.clock.get_fps())
        average = 0
        for f in self.fps:
            average += f
        average /= len(self.fps)
        return average

    def display_fps(self):
        pygame.display.set_caption("drc-sim - fps: " + str(round(self.get_average_fps())))

    def send_command(self, name, data):
        self.CMD_S.sendall(name + "\n" + str(data) + "\n")

    def check_input(self):
        buttonbytes = controller.get_button_input()
        l3r3bytes = controller.get_l3_r3_input()
        timestamp = time.time()
        if buttonbytes > 0:
            self.send_command("BUTTON", str(buttonbytes) + "-" + str(timestamp))
        if l3r3bytes > 0:
            self.send_command("L3R3", str(l3r3bytes) + "-" + str(timestamp))

    # noinspection PyUnusedLocal,SpellCheckingInspection
    def pyaudio_callback(self, in_data, frame_count, time_info, status):
        return self.audio_bytes, pyaudio.paContinue

    def update_audio(self):
        try:
            audio_bytes = self.get_data_from_sock(self.AUD_S)
        except IOError, e:
            print "[Audio]", e
            return
        if audio_bytes:
            self.audio_bytes = audio_bytes

    def run(self):
        self.check_quit()
        self.update_video()
        self.update_audio()
        self.check_input()
        self.display_fps()


frontend = Frontend()

while True:
    frontend.run()
