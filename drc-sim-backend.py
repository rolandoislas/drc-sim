import sys

from src.server.control.gamepad import Gamepad

gamepad = Gamepad()
while True:
    try:
        gamepad.update()
    except KeyboardInterrupt:
        gamepad.close()
        sys.exit()

