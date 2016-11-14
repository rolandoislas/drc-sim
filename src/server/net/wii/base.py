class ServiceBase(object):
    def __init__(self):
        self.seq_id_expect = None

    def update_seq_id(self, seq_id):
        ret = True
        if self.seq_id_expect is None:
            self.seq_id_expect = seq_id
        elif self.seq_id_expect != seq_id:
            ret = False
        self.seq_id_expect = (seq_id + 1) & 0x3ff
        return ret

    def close(self):
        pass

    def update(self, packet):
        pass
