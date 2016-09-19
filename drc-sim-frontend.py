import pyaudio
import pygame
import socket
import sys
import time

from control import controller
from data import constants

IP = "0.0.0.0"


def client(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    return sock


VID_S = client(IP, constants.SERVER_PORT_VID)
AUD_S = client(IP, constants.SERVER_PORT_AUD)
CMD_S = client(IP, constants.SERVER_PORT_CMD)

pygame.init()
screen = pygame.display.set_mode((constants.WII_VIDEO_WIDTH, constants.WII_VIDEO_HEIGHT))
pygame.display.set_caption("drc-sim")
clock = pygame.time.Clock()
input_time = 0
sample_buffer = None
fps = []


def check_quit():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()


def get_buffer_from_sock(sock, send_data=0):
    sock.send(str(send_data))
    data_buffer = sock.recv(4096)
    # format LENGTH\nRAWDATA
    length = int(str.split(data_buffer, "\n")[0] if len(data_buffer) > 0 else 0)
    data_buffer = data_buffer[len(str(length)) + 1:]
    while True:
        if len(data_buffer) == length:
            break
        data_buffer += sock.recv(4096)
    return data_buffer


def update_screen():
    image_buffer = get_buffer_from_sock(VID_S)
    try:
        # Convert to image
        image = pygame.image.fromstring(image_buffer, (854, 480), "RGB")
    except Exception, e:
        print e
    else:
        screen.blit(image, (0, 0))
        pygame.display.flip()
        # Update clock TODO get actual fps
        clock.tick()


def get_average_fps():
    global fps
    if len(fps) > 1000:
        fps = fps[1:]
    fps.append(clock.get_fps())
    average = 0
    for f in fps:
        average += f
    average /= len(fps)
    return average


def display_fps():
    pygame.display.set_caption("drc-sim - fps: " + str(round(get_average_fps())))


def send_command(name, data):
    CMD_S.send(name + "\n" + str(data) + "\n")


def check_input():
    buttonbytes = controller.get_button_input()
    l3r3bytes = controller.get_l3_r3_input()
    timestamp = time.time()
    if buttonbytes > 0:
        send_command("BUTTON", str(buttonbytes) + "-" + str(timestamp))
    if l3r3bytes > 0:
        send_command("L3R3", str(l3r3bytes) + "-" + str(timestamp))


# noinspection PyUnusedLocal,SpellCheckingInspection
def pyaudio_callback(in_data, frame_count, time_info, status):
    return sample_buffer[0], pyaudio.paContinue

p = pyaudio.PyAudio()
stream = None


def update_audio():
    global sample_buffer, stream
    timestamp = sample_buffer[1] if sample_buffer is not None and len(sample_buffer) > 0 else 0
    s_buffer = get_buffer_from_sock(AUD_S, timestamp)
    if s_buffer is not None:
        bytes_array = str.split(s_buffer, "----")
        sample_buffer = (bytes_array[0], bytes_array[1])
        if stream is None:
            stream = p.open(format=pyaudio.paInt16,
                            channels=2,
                            rate=48000,
                            output=True,
                            frames_per_buffer=416 * 2,
                            stream_callback=pyaudio_callback)
            stream.start_stream()


while True:
    check_quit()
    update_screen()
    update_audio()
    check_input()
    display_fps()
