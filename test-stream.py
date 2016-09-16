import pygame
import socket
import sys

IP = "127.0.0.1"
VIDEO_PORT = 50000

pygame.init()
screen = pygame.display.set_mode((854, 480))
pygame.display.set_caption("test-stream")

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
    # Get data
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((IP, VIDEO_PORT))
    imageBuffer = ""
    bytesRead = 0
    while bytesRead < 1229760:
        data = client.recv(1229760)
        if not data:
            break
        bytesRead += len(data)
        imageBuffer += data
    # Convert to image
    image = pygame.image.fromstring(imageBuffer, (854, 480), "RGB")
    screen.blit(image, (0, 0))
    pygame.display.flip()
