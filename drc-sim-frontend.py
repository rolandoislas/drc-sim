import pygame
import time
import socket
import sys

from control import controller

IP = "0.0.0.0"
VIDEO_PORT = 50000
CMD_PORT = 50002


def client(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    return sock


VID_S = client(IP, VIDEO_PORT)
CMD_S = client(IP, CMD_PORT)

pygame.init()
screen = pygame.display.set_mode((854, 480))
pygame.display.set_caption("test-stream")
clock = pygame.time.Clock()


def check_quit():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()


def update_screen():
    # Get data
    image_buffer = ""
    bytes_read = 0
    VID_S.sendto("", (IP, VIDEO_PORT))
    while bytes_read < 1229760:
        data = VID_S.recv(1229760)
        if not data:
            break
        bytes_read += len(data)
        image_buffer += data
    # Convert to image
    print str(len(image_buffer))
    if len(image_buffer) == 0:
        time.sleep(1)
        return
    image = pygame.image.fromstring(image_buffer, (854, 480), "RGB")
    screen.blit(image, (0, 0))
    pygame.display.flip()


def tick_clock():
    clock.tick()
    pygame.display.set_caption("test-stream - fps: " + str(round(clock.get_fps())))


def check_input():
    buttonBytes = controller.get_input()
    l3r3Bytes = controller.get_l3_r3_input()


while True:
    check_quit()
    update_screen()
    check_input()
    tick_clock()

