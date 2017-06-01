import os
import subprocess
from tkinter import Button, CENTER, messagebox

from src.server.data import constants
from src.server.ui.gui.frame.frame_tab import FrameTab


class FrameLog(FrameTab):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.button_log = Button(self, text="Open Log in Console")
        self.button_log.bind("<Button-1>", self.button_clicked)
        self.button_log.place(relx=0.5, rely=0.5, anchor=CENTER)
        self.log = None

    # noinspection PyUnusedLocal
    def button_clicked(self, event):
        tail = ["x-terminal-emulator", "-e", "tail", "-f"]
        for file in ("drcsim", "cli", "gui", "wpa", "backend", "drc_sim_c"):
            tail.append(os.path.join(constants.PATH_LOG_DIR, file + ".log"))
        self.deactivate()
        try:
            self.log = subprocess.Popen(tail, stdout=open(os.devnull, "w"), stderr=subprocess.PIPE)
        except FileNotFoundError:
            messagebox.showerror("Log Error", "Could not open log window.")

    def activate(self):
        pass

    def deactivate(self):
        pass

    def kill_other_tabs(self):
        return False
