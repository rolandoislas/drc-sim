from tkinter import PhotoImage, Button, END, messagebox
from tkinter.ttk import Entry, Combobox, Label

from src.server.data import constants
from src.server.data.resource import Resource
from src.server.ui.cli.cli_main import CliMain
from src.server.ui.gui.frame.frame_tab import FrameTab
from src.server.util.interface_util import InterfaceUtil
from src.server.util.logging.logger_gui import LoggerGui
from src.server.util.wpa_supplicant import WpaSupplicant


class FrameGetKey(FrameTab):
    def __init__(self, master=None, **kw):
        FrameTab.__init__(self, master, **kw)
        self.wpa_supplicant = None
        self.getting_psk = False
        # Widgets
        button_size = 50
        # Spade
        self.button_spade = Button(self, width=button_size, height=button_size)
        self.button_spade.image = self.get_image("image/spade.gif", button_size, button_size)
        self.button_spade.config(image=self.button_spade.image)
        self.button_spade.number = 0
        # Heart
        self.button_heart = Button(self, width=button_size, height=button_size)
        self.button_heart.image = self.get_image("image/heart.gif", button_size, button_size)
        self.button_heart.config(image=self.button_heart.image)
        self.button_heart.number = 1
        # Diamond
        self.button_diamond = Button(self, width=button_size, height=button_size)
        self.button_diamond.image = self.get_image("image/diamond.gif", button_size, button_size)
        self.button_diamond.config(image=self.button_diamond.image)
        self.button_diamond.number = 2
        # Clover
        self.button_clover = Button(self, width=button_size, height=button_size)
        self.button_clover.image = self.get_image("image/clover.gif", button_size, button_size)
        self.button_clover.config(image=self.button_clover.image)
        self.button_clover.number = 3
        # Delete
        self.button_delete = Button(self, text="Delete")
        # Code
        self.entry_pair_code = Entry(self, state="readonly")
        # Status Message
        self.status_message = Label(self, state="readonly")
        # interface dropdown
        self.dropdown_wii_u = Combobox(self, state="readonly")
        # Events
        self.button_spade.bind("<Button-1>", self.button_clicked)
        self.button_heart.bind("<Button-1>", self.button_clicked)
        self.button_diamond.bind("<Button-1>", self.button_clicked)
        self.button_clover.bind("<Button-1>", self.button_clicked)
        self.button_delete.bind("<Button-1>", self.button_delete_clicked)
        # Grid
        self.button_spade.grid(column=0, row=0)
        self.button_heart.grid(column=1, row=0)
        self.button_diamond.grid(column=2, row=0)
        self.button_clover.grid(column=3, row=0)
        self.button_delete.grid(column=4, row=0)
        self.entry_pair_code.grid(column=0, row=1, columnspan=5)
        self.status_message.grid(column=0, row=3, columnspan=5)
        self.dropdown_wii_u.grid(column=0, row=2, columnspan=5)

    # noinspection PyUnusedLocal
    def button_delete_clicked(self, event):
        self.set_code_text(self.entry_pair_code.get()[:len(self.entry_pair_code.get()) - 1])

    def button_clicked(self, event):
        if self.getting_psk:
            messagebox.showerror("Running", "A pairing attempt is already im progress.")
            return
        number = str(event.widget.number)
        LoggerGui.debug("A suit button was clicked")  # Don't log numbers as the code can be derived from that
        code = self.entry_pair_code.get()
        code += number
        self.set_code_text(code)
        wii_u_interface = self.dropdown_wii_u.get()
        if not wii_u_interface:
            messagebox.showerror("No Interface", "An interface must be selected.")
            self.activate()
            return
        try:
            InterfaceUtil.get_mac(wii_u_interface)
        except ValueError:
            messagebox.showerror("Interface Error", "The selected Interface is no longer available.")
            self.activate()
            return
        if InterfaceUtil.is_managed_by_network_manager(wii_u_interface):
            set_unmanaged = messagebox.askokcancel(
                "Managed Interface", "This interface is managed by Network Manager. To use it with DRC Sim it needs "
                                     "to be set to unmanaged. Network Manager will not be able to control the interface"
                                     " after this.\nSet %s to unmanaged?" % wii_u_interface)
            if set_unmanaged:
                InterfaceUtil.set_unmanaged_by_network_manager(wii_u_interface)
            else:
                messagebox.showerror("Managed Interface", "Selected Wii U interface is managed by Network Manager.")
                self.activate()
                return
        if len(code) == 4:
            self.getting_psk = True
            self.set_code_text("")
            self.get_psk(code, wii_u_interface)

    def get_psk(self, code, interface):
        LoggerGui.debug("Attempting to get PSK")  # Don't log code
        CliMain.create_temp_config_file()
        self.wpa_supplicant = WpaSupplicant()
        self.wpa_supplicant.add_status_change_listener(self.wpa_status_changed)
        self.wpa_supplicant.get_psk(constants.PATH_CONF_CONNECT_TMP, interface, code)

    def wpa_status_changed(self, status):
        LoggerGui.debug("Wpa status changed to %s", status)
        if status == WpaSupplicant.NOT_FOUND:
            self.deactivate()
            self.activate()
            messagebox.showerror("Scan", "No Wii U found.")
        elif status == WpaSupplicant.TERMINATED:
            self.deactivate()
            self.activate()
            messagebox.showerror("Auth Fail", "Could not authenticate. Check the entered PIN.")
        elif status == WpaSupplicant.FAILED_START:
            self.deactivate()
            self.activate()
            messagebox.showerror("Error", "An unexpected error occurred.")
        elif status == WpaSupplicant.DISCONNECTED:
            self.deactivate()
            self.activate()
            messagebox.showerror("Auth Saved", "Successfully paired with Wii U.")
        elif status == WpaSupplicant.SCANNING:
            self.status_message["text"] = "Scanning"
        elif status == WpaSupplicant.CONNECTING:
            self.status_message["text"] = "Connecting"

    def activate(self):
        LoggerGui.debug("FrameTab activate called")
        self.getting_psk = False
        self.set_code_text("")
        if not self.wpa_supplicant or not self.wpa_supplicant.get_status():
            self.status_message["text"] = ""
        self.dropdown_wii_u["values"] = InterfaceUtil.get_wiiu_compatible_interfaces()

    def deactivate(self):
        LoggerGui.debug("FrameTab deactivate called")
        self.status_message["text"] = ""
        self.getting_psk = False
        if self.wpa_supplicant:
            self.wpa_supplicant.stop()
            self.wpa_supplicant = None

    @staticmethod
    def get_image(location, width, height):
        image = PhotoImage(data=Resource(location).resource)
        orig_width = image.width()
        orig_height = image.height()
        image = image.zoom(width, height)
        image = image.subsample(orig_width, orig_height)
        return image

    def set_code_text(self, text):
        self.entry_pair_code.config(state="normal")
        self.entry_pair_code.delete(0, END)
        self.entry_pair_code.insert(0, text)
        self.entry_pair_code.config(state="readonly")

    def kill_other_tabs(self):
        return True
