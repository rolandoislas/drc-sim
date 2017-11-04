import os
import time

from src.server.data import constants
from src.server.data.args import Args
from src.server.data.resource import Resource
from src.server.util.drc_sim_c import DrcSimC
from src.server.util.interface_util import InterfaceUtil
from src.server.util.logging.logger_cli import LoggerCli
from src.server.util.process_util import ProcessUtil
from src.server.util.wpa_supplicant import WpaSupplicant


class CliMain:
    def __init__(self):
        self.getting_key = False
        self.drc_sim_c = None
        self.wpa_supplicant = None

    def start(self):
        if Args.args.run_server:
            self.run_server()
        elif Args.args.get_key:
            self.get_key()
        else:
            self.stop()

    def stop(self):
        LoggerCli.info("Stopping")
        ProcessUtil.call(["killall", "dhclient"])
        self.getting_key = False
        if self.drc_sim_c:
            self.drc_sim_c.stop()
        if self.wpa_supplicant:
            self.wpa_supplicant.stop()

    def run_server(self):
        LoggerCli.info("Starting server")
        normal_interface = Args.args.normal_interface
        wii_u_interface = Args.args.wii_u_interface
        self.check_interfaces(normal_interface, wii_u_interface)
        self.prompt_unmanaged(wii_u_interface)
        self.wpa_supplicant = WpaSupplicant()
        self.wpa_supplicant.connect(constants.PATH_CONF_CONNECT, wii_u_interface)
        self.wpa_supplicant.add_status_change_listener(self.status_changed)
        InterfaceUtil.dhclient(wii_u_interface)
        InterfaceUtil.set_metric(wii_u_interface, 1)
        InterfaceUtil.set_metric(normal_interface, 0)
        self.drc_sim_c = DrcSimC()
        self.drc_sim_c.set_region(Args.args.region)
        self.drc_sim_c.add_status_change_listener(self.drc_sim_c_status_changed)
        self.drc_sim_c.start()
        while self.drc_sim_c.running:
            time.sleep(1)

    def drc_sim_c_status_changed(self, status):
        if status == DrcSimC.STOPPED:
            self.stop()

    @staticmethod
    def check_interfaces(normal_interface, wii_u_interface):
        if normal_interface == wii_u_interface:
            LoggerCli.throw(Exception("The Wii U and normal interfaces cannot be the same."))
        try:
            InterfaceUtil.get_mac(normal_interface)
            InterfaceUtil.get_mac(wii_u_interface)
        except ValueError:
            LoggerCli.throw(Exception("Invalid interface selected."))

    def status_changed(self, status):
        LoggerCli.info("Connection status changed to %s.", status)
        if status in (WpaSupplicant.TERMINATED, WpaSupplicant.NOT_FOUND, WpaSupplicant.DISCONNECTED,
                      WpaSupplicant.FAILED_START):
            self.stop()

    def status_changed_key(self, status):
        LoggerCli.info("Connection status changed to %s.", status)
        if status == WpaSupplicant.DISCONNECTED:
            LoggerCli.info("Successfully received PSK from the Wii U.")
            self.stop()
        elif status in (WpaSupplicant.TERMINATED, WpaSupplicant.NOT_FOUND, WpaSupplicant.FAILED_START):
            self.stop()

    def get_key(self):
        LoggerCli.info("Getting key")
        wii_u_interface = Args.args.wii_u_interface
        try:
            InterfaceUtil.get_mac(wii_u_interface)
        except ValueError:
            LoggerCli.throw(Exception("Invalid interface selected."))
        if len(Args.args.wps_pin) != 4:
            LoggerCli.throw(Exception("WPS PIN should be 4 digits"))
        self.prompt_unmanaged(wii_u_interface)
        self.create_temp_config_file()
        self.wpa_supplicant = WpaSupplicant()
        self.wpa_supplicant.get_psk(constants.PATH_CONF_CONNECT_TMP, wii_u_interface, Args.args.wps_pin)
        self.wpa_supplicant.add_status_change_listener(self.status_changed_key)
        self.getting_key = True
        while self.getting_key:
            time.sleep(1)

    @staticmethod
    def prompt_unmanaged(interface):
        if not InterfaceUtil.is_managed_by_network_manager(interface):
            return
        LoggerCli.info("The interface \"%s\" is managed by Network Manager. It must be set to "
                       "unmanaged to function with DRC Sim. Network manager will not be able to "
                       "use this interface after it is set to unmanaged.", interface)
        response = input("Set %s as unmanaged? (y/n)" % interface)
        LoggerCli.debug(response)
        if response in ("y", "yes", "Y", "Yes", "YES"):
            InterfaceUtil.set_unmanaged_by_network_manager(interface)
        else:
            LoggerCli.throw(Exception("Interface is managed by Network Manager."))

    @classmethod
    def create_temp_config_file(cls):
        if not os.path.exists(constants.PATH_TMP):
            os.mkdir(constants.PATH_TMP)
        tmp_conf = open(constants.PATH_CONF_CONNECT_TMP, "w")
        tmp_conf.write(Resource("config/get_psk.conf").resource)
        tmp_conf.close()
