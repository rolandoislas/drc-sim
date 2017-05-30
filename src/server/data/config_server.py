from src.server.data.config import Config


class ConfigServer:
    scan_timeout = None
    config = Config()

    def __init__(self):
        pass

    @classmethod
    def load(cls):
        cls.config.load("~/.drc-sim/server.conf")
        # General
        cls.scan_timeout = cls.config.get_int("GENERAL", "scan_timeout", 0, 60 * 5, 60 * 2, "Sets the time they server "
                                                                                            "is allowed to scan for the"
                                                                                            "Wii U network")

    @classmethod
    def save(cls):
        cls.config.save()
