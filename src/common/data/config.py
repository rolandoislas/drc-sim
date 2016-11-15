class Config:
    stream_audio = True
    input_delay = 0.1  # 3 low - 2 lan - 1 loopback
    quality = 75  # 5 low - 75 lan - 100 loopback
    fps = 30  # 10 low - 30 lan - 60 loopback

    def __init__(self):
        pass

    @classmethod
    def get_fps(cls):
        return cls.fps

    @classmethod
    def get_quality(cls):
        return cls.quality

    @classmethod
    def get_input_delay(cls):
        return cls.input_delay

    @classmethod
    def do_stream_audio(cls):
        return cls.stream_audio
