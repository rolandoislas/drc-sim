import pygame
from PIL import Image
from io import BytesIO

from src.common.data import constants


class VideoHandler:
    def __init__(self):
        pass

    def close(self):
        pass

    @staticmethod
    def update(data):
        size = (constants.WII_VIDEO_WIDTH, constants.WII_CAMERA_HEIGHT)
        try:
            image_io = BytesIO(data)
            image = Image.open(image_io)
            surface = pygame.image.frombuffer(image.tobytes(), size, "RGB")
        except IOError:
            try:
                surface = pygame.image.frombuffer(data, size, "RGB")
            except ValueError:
                print "[VIDEO] Skipping frame"
                return
        surface = pygame.transform.smoothscale(surface, pygame.display.get_surface().get_size())
        pygame.display.get_surface().blit(surface, (0, 0))
        pygame.display.flip()
