from tkinter import Label

from src.server.data import constants
from src.server.ui.gui.frame.frame_tab import FrameTab


class FrameAbout(FrameTab):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.text_name = Label(self, text=constants.NAME)
        self.text_version = Label(self, text="v" + constants.VERSION)
        self.text_license = Label(self,
                                  text="%s is free software: you can\n" % constants.NAME +
                                       "redistribute it and/or modify it under the\n"
                                       "terms of the GNU General Public License as\n"
                                       "published by the Free Software Foundation,\n"
                                       "either version 2 of the License, or\n"
                                       "(at your option) any later version."
                                  )

        self.text_name.grid(row=0, column=0)
        self.text_version.grid(row=1, column=0)
        self.text_license.grid(row=2, column=0)
        self.grid_columnconfigure(0, weight=1)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def kill_other_tabs(self):
        return False
