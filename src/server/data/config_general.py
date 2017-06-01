from src.server.data.config import Config


class ConfigGeneral:
    scan_timeout = None
    config = Config()
    stream_audio = None
    input_delay = None
    video_quality = None
    stream_video = None

    def __init__(self):
        pass

    @classmethod
    def load(cls):
        cls.config.load("~/.drc-sim/server.conf")
        # Audio
        cls.stream_audio = cls.config.get_boolean("AUDIO", "stream", True, "Stream audio to clients")
        # Input
        cls.input_delay = cls.config.get_int("INPUT", "delay", 0, 1000, 100, "Amount of time in milliseconds to send "
                                                                             "input to the Wii U")
        # Video
        cls.video_quality = cls.config.get_int("VIDEO", "quality", 0, 100, 75, "Quality of video stream.\n"
                                                                               "5/10/15 low - 75 lan - 100 loopback\n"
                                                                               "There is latency at 100.")
        cls.stream_video = cls.config.get_boolean("VIDEO", "stream", True, "Stream video to clients")
        # General
        cls.scan_timeout = cls.config.get_int("GENERAL", "scan_timeout", 0, 60 * 5, 60 * 2, "Sets the time "
                                                                                            "allowed to scan for the "
                                                                                            "Wii U")

    @classmethod
    def save(cls):
        cls.config.save()
