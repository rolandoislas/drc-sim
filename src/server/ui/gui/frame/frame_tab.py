from tkinter.ttk import Frame


class FrameTab(Frame):
    def __init__(self, master=None, **kw):
        Frame.__init__(self, master, **kw)

    def activate(self):
        raise NotImplementedError()

    def deactivate(self):
        raise NotImplementedError()

    def kill_other_tabs(self):
        raise NotImplementedError()
