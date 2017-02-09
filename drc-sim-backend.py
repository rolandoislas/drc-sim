import sys

from src.server.data.args import Args
from src.server.control.gamepad import Gamepad


class Backend:

    def __init__(self):
        self.gamepad = Gamepad()
        Args.parse_args()

    def run(self):
        self.gamepad.update()

    def close(self):
        self.gamepad.close()

backend = Backend()
while True:
    try:
        backend.run()
    except KeyboardInterrupt:
        backend.close()
        sys.exit()

