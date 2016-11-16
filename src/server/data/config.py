from src.common.data.config import Config


class ConfigServer:
    config = Config()
    stream_audio = None
    input_delay = None
    quality = None
    fps = None

    def __init__(self):
        pass

    @classmethod
    def load(cls):
        cls.config.load("~/.drc-sim/server.conf")
        cls.stream_audio = cls.config.get_boolean("AUDIO", "stream", True, "Stream audio to clients")
        cls.input_delay = cls.config.get_float("INPUT", "delay", 0, 1, 0.1, "Amount of time to send input to Wii")
        cls.quality = cls.config.get_int("VIDEO", "quality", 1, 100, 75, "Quality of video stream. Sends uncompressed "
                                                                         "data at 100\n"
                                                                         "5/10/15 low - 75 lan - 100 loopback")
        cls.fps = cls.config.get_int("VIDEO", "fps", 1, 60, 30, "FPS of video stream. No limit if set to 60\n"
                                                                "10 low - 30 lan - 60 loopback")

    @classmethod
    def save(cls):
        cls.config.save()
