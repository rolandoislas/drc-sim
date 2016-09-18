import pygame
import time
import socket
import sys

from control import controller
from data import constants

IP = "0.0.0.0"


def client(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    return sock


VID_S = client(IP, constants.SERVER_PORT_VID)
CMD_S = client(IP, constants.SERVER_PORT_CMD)

pygame.init()
screen = pygame.display.set_mode((854, 480))
pygame.display.set_caption("test-stream")
clock = pygame.time.Clock()
input_time = 0


def check_quit():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()


def update_screen():
    # Get data
    image_buffer = ""
    bytes_read = 0
    VID_S.send("0")
    while bytes_read < 1229760:
        data = VID_S.recv(1229760)
        if not data:
            time.sleep(1)
            return
        bytes_read += len(data)
        image_buffer += data
    # Convert to image
    image = pygame.image.fromstring(image_buffer, (854, 480), "RGB")
    screen.blit(image, (0, 0))
    pygame.display.flip()


def tick_clock():
    clock.tick()
    pygame.display.set_caption("drc-sim - fps: " + str(round(clock.get_fps())))


def send_command(name, data):
    CMD_S.send(name + "\n" + str(data) + "\n")


def check_input():
    buttonbytes = controller.get_input()
    l3r3bytes = controller.get_l3_r3_input()
    timestamp = time.time()
    if buttonbytes > 0:
        send_command("BUTTON", str(buttonbytes) + "-" + str(timestamp))
    if l3r3bytes > 0:
        send_command("L3R3", str(l3r3bytes) + "-" + str(timestamp))

while True:
    check_quit()
    update_screen()
    check_input()
    tick_clock()

