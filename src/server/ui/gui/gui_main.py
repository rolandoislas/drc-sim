import Tkinter
from ttk import Notebook

from src.server.data.resource import Resource
from src.server.ui.gui.frame.frame_get_key import FrameGetKey
from src.server.ui.gui.frame.frame_run_server import FrameRunServer
from src.server.util.logging.logger_gui import LoggerGui


class GuiMain:
    def __init__(self):
        Tkinter.Tk.report_callback_exception = self.throw
        # Main window
        self.destroyed = False
        LoggerGui.info("Initializing GUI")
        self.main_window = Tkinter.Tk()
        self.main_window.wm_title("DRC Sim Server")
        icon = Tkinter.PhotoImage(data=Resource("image/icon.png").resource)
        self.main_window.tk.call("wm", "iconphoto", self.main_window, icon)
        self.main_window.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Notebook
        self.tab_id = None
        self.notebook = Notebook(self.main_window, width=300, height=150)
        self.notebook.grid(column=0, row=0)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        # Run Server Frame
        self.frame_run_server = FrameRunServer(self.notebook)
        self.notebook.add(self.frame_run_server, text="Run Server")
        # Get Key Frame
        self.frame_get_key = FrameGetKey(self.notebook)
        self.notebook.add(self.frame_get_key, text="Get Key")

    @staticmethod
    def throw(*args):
        for arg in args:
            if isinstance(arg, Exception):
                LoggerGui.throw(arg)

    def after(self):
        self.main_window.after(1000, self.after)

    def start(self):
        LoggerGui.info("Opening GUI")
        self.after()
        self.main_window.mainloop()
        LoggerGui.info("GUI Closed")

    def stop(self):
        self.on_closing()

    def on_closing(self):
        if self.destroyed:
            return
        self.destroyed = True
        LoggerGui.info("Closing GUI")
        if self.tab_id in self.notebook.children:
            self.notebook.children[self.tab_id].deactivate()
        try:
            self.main_window.destroy()
        except Exception, e:
            LoggerGui.exception(e)

    def on_tab_changed(self, event):
        tab_id = self.notebook.select()
        tab_index = self.notebook.index(tab_id)
        tab_name = self.notebook.tab(tab_index, "text")
        LoggerGui.debug("Notebook tab changed to \"%s\" with id %d", tab_name, tab_index)
        if self.tab_id:
            self.notebook.children[self.tab_id].deactivate()
        self.tab_id = tab_id.split(".")[len(tab_id.split(".")) - 1]
        self.notebook.children[self.tab_id].activate()
