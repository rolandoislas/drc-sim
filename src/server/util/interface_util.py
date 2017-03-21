import netifaces
import os

from src.server.data import constants
from src.server.util.logging.logger import Logger
from src.server.util.os_util import OsUtil
from src.server.util.process_util import ProcessUtil


class InterfaceUtil:
    def __init__(self):
        pass

    @classmethod
    def get_wiiu_compatible_interfaces(cls):
        """
        Returns a list of interfaces that can operate on the 5GHz spectrum
        :return: array of interface names
        """
        all_interfaces = cls.get_all_interfaces()
        compatible_interfaces = []
        for interface in all_interfaces:
            if cls.is_interface_wiiu_compatible(interface):
                compatible_interfaces.append(interface)
        return compatible_interfaces

    @classmethod
    def get_all_interfaces(cls):
        """
        Gets a list of all system network interfaces
        :return: array of interface names
        """
        interfaces = []
        for interface in netifaces.interfaces():
            interfaces.append(interface)
        return interfaces

    @classmethod
    def is_interface_wiiu_compatible(cls, interface):
        if not OsUtil.is_linux():
            Logger.extra("Ignoring interface compatibility check for %s", interface)
            return False
        frequency_info = ProcessUtil.get_output(["iwlist", interface, "frequency"])
        return "5." in frequency_info
        # TODO check for 802.11n compliance

    @classmethod
    def get_ip(cls, interface):
        return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]

    @classmethod
    def get_mac(cls, interface):
        return netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]["addr"]

    @classmethod
    def set_metric(cls, interface, metric):
        ProcessUtil.call(["ifmetric", interface, str(metric)])

    @classmethod
    def dhclient(cls, interface):
        ProcessUtil.call(["killall", "dhclient"])
        ProcessUtil.call(["dhclient", interface])

    @classmethod
    def is_managed_by_network_manager(cls, interface):
        if not os.path.exists(constants.PATH_CONF_NETWORK_MANAGER):
            Logger.debug("Network manager config not found.")
            return False
        conf = open(constants.PATH_CONF_NETWORK_MANAGER)
        conf_data = conf.readlines()
        conf.close()
        for line in conf_data:
            if line.startswith("unmanaged") and "mac:" + cls.get_mac(interface) in line:
                Logger.debug("Interface \"%s\" is unmanaged by network manager.", interface)
                return False
        return True

    @classmethod
    def set_unmanaged_by_network_manager(cls, interface):
        Logger.debug("Adding interface \"%s-%s\" as an unmanaged interface to network manager", interface,
                     cls.get_mac(interface))
        conf = open(constants.PATH_CONF_NETWORK_MANAGER, "a")
        conf.writelines(["[keyfile]\n", "unmanaged-devices=mac:" + cls.get_mac(interface) + "\n"])
        conf.close()
        ProcessUtil.call(["service", "network-manager", "restart"])
