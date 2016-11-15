import array
import pyaudio


class AudioHandler:
    def __init__(self):
        self.pyaudio = pyaudio.PyAudio()
        self.stream = None
        self.is_streaming = False

        self.pa_num_bufs = 15
        self.pa_ring = [array.array('H', '\0' * 416 * 2)] * self.pa_num_bufs
        self.pa_wpos = self.pa_rpos = 0

    def close(self):
        self.stream.stop_stream()
        self.stream.close()

    def update(self, data):
        self.pa_ring[self.pa_rpos] = array.array('H', data)
        self.pa_rpos += 1
        self.pa_rpos %= self.pa_num_bufs
        if self.is_streaming and not self.stream.is_active():
            self.stream.close()
            self.is_streaming = False

        if not self.is_streaming:
            self.stream = self.pyaudio.open(format=pyaudio.paInt16,
                                            channels=2,
                                            rate=48000,
                                            output=True,
                                            frames_per_buffer=416 * 2,
                                            stream_callback=self.pa_callback,
                                            #start=False
                                            )
            #self.stream.start_stream()
            self.is_streaming = True

    def pa_callback(self, in_data, frame_count, time_info, status):
        samples = self.pa_ring[self.pa_wpos]
        self.pa_wpos += 1
        self.pa_wpos %= self.pa_num_bufs
        samples.extend(self.pa_ring[self.pa_wpos])
        self.pa_wpos += 1
        self.pa_wpos %= self.pa_num_bufs
        return samples, pyaudio.paContinue
