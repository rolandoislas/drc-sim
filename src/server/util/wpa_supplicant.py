import re
import subprocess
import time
from threading import Thread

import pexpect

from src.server.data import constants
from src.server.data.config_server import ConfigServer
from src.server.util.logging.logger_wpa import LoggerWpa
from src.server.util.process_util import ProcessUtil
from src.server.util.status_sending_thread import StatusSendingThread


class WpaSupplicant(StatusSendingThread):
    UNKNOWN = "UNKNOWN"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    TERMINATED = "TERMINATED"
    DISCONNECTED = "DISCONNECTED"
    SCANNING = "SCANNING"
    NOT_FOUND = "NOT_FOUND"
    FAILED_START = "FAILED_START"

    def __init__(self):
        """
        Helper for interacting with wpa_supplicant_drc and wpa_cli_drc.
        """
        super().__init__()
        self.time_scan = 0
        self.time_start = 0
        self.mac_addr_regex = re.compile('^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})')
        self.wiiu_ap_regex = re.compile('^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})(\s*\d*\s*-*\d*\s*)'
                                        '(\[WPA2-PSK-CCMP\])?'
                                        '(\[ESS\])(\s*)(WiiU|\\\\x00)(.+)$')  # \x00 is escaped (\\x00)
        self.running = False
        self.status = self.UNKNOWN
        self.status_check_thread = None
        self.wpa_supplicant_process = None
        self.psk_thread = None
        self.psk_thread_cli = None

    def connect(self, conf_path, interface, status_check=True):
        """
        Starts a thread that connects to the Wii U.
        Status:
          FAILED_START: wpa_supplicant_drc did not initialize
          SCANNING: wpa_supplicant_drc is scanning
          CONNECTED: wpa_supplicant_drc is connected to an AP
          CONNECTING: wpa_supplicant_drc is authenticating
          TERMINATED: wpa_supplicant_drc was found by the T-1000 Cyberdyne Systems Model 101
          NOT_FOUND: wpa_supplicant_drc could not find a Wii U AP
          UNKNOWN: wpa_supplicant_drc is in a state that is unhandled - it will be logged
        :return: None
        """
        LoggerWpa.debug("Connect called")
        self.running = True
        self.unblock_wlan()
        self.kill_wpa()
        command = ["wpa_supplicant_drc", "-Dnl80211", "-i", interface, "-c", conf_path]
        if LoggerWpa.get_level() == LoggerWpa.FINER:
            command.append("-d")
        elif LoggerWpa.get_level() == LoggerWpa.VERBOSE:
            command.append("-dd")
        LoggerWpa.debug("Starting wpa supplicant")
        self.wpa_supplicant_process = subprocess.Popen(command, stdout=open(constants.PATH_LOG_WPA, "w"),
                                                       stderr=subprocess.STDOUT)
        LoggerWpa.debug("Started wpa supplicant")
        if status_check:
            LoggerWpa.debug("Starting status check thread")
            self.status_check_thread = Thread(target=self.check_status, name="WPA Status Check Thread")
            self.status_check_thread.start()

    def check_status(self):
        """
        Thread that checks WPA status every second
        Updates 
        :return: None
        """
        while self.running:
            wpa_status = self.wpa_cli("status")
            scan_results = self.wpa_cli("scan_results")
            not_started_message = "Failed to connect to non-global ctrl_ifname"
            LoggerWpa.finer("Scan Results: %s", scan_results)
            LoggerWpa.finer("Status: %s", wpa_status)
            # process is dead or wpa_supplicant has not started
            if self.wpa_supplicant_process.poll() or not_started_message in scan_results:
                LoggerWpa.finer("%d seconds until start timeout", 30 - self.time_start)
                # wait for wpa_supplicant to initialize
                if self.time_start >= 5:
                    status = self.FAILED_START
                else:
                    status = self.status
                    self.time_start += 1
            # scanning
            elif not self.scan_contains_wii_u(scan_results) or "wpa_state=SCANNING" in wpa_status:
                LoggerWpa.finer("%d seconds until scan timeout", ConfigServer.scan_timeout - self.time_scan)
                # timeout scan
                if self.time_scan >= ConfigServer.scan_timeout:
                    status = self.NOT_FOUND
                else:
                    status = self.SCANNING
                    self.time_scan += 1
            elif "wpa_state=COMPLETED" in wpa_status:
                status = self.CONNECTED
                self.time_scan = 0  # forces a disconnect - might need to be handled better
            elif "wpa_state=AUTHENTICATING" in wpa_status or "wpa_state=ASSOCIATING" in wpa_status:
                status = self.CONNECTING
            elif "wpa_state=DISCONNECTED" in wpa_status:
                status = self.DISCONNECTED
            else:
                LoggerWpa.extra("WPA status: %s", wpa_status)
                status = self.UNKNOWN
            self.set_status(status)
            time.sleep(1)

    @staticmethod
    def kill_wpa():
        """
        Makes a system call to kill wpa_supplicant_drc
        :return: None
        """
        ProcessUtil.call(["killall", "wpa_supplicant_drc"])

    @staticmethod
    def unblock_wlan():
        """
        Make a system call to unblock wlan
        :return: None
        """
        ProcessUtil.call(["rfkill", "unblock", "wlan"])

    @staticmethod
    def wpa_cli(command):
        """
        Makes a system call to wpa_cli_drc
        :param command: command to pass to wpa_cli_drc
        :return: command output
        """
        if isinstance(command, str):
            command = [command]
        return ProcessUtil.get_output(["wpa_cli_drc", "-p", "/var/run/wpa_supplicant_drc"] + command, silent=True)

    def stop(self):
        """
        Stops any background thread that is running
        :return: None
        """
        if not self.running:
            LoggerWpa.debug("Ignored stop request: already stopped")
            return
        self.running = False
        if self.status_check_thread:
            LoggerWpa.debug("Stopping wpa status check")
            try:
                self.status_check_thread.join()
            except RuntimeError as e:
                LoggerWpa.exception(e)
        if self.psk_thread_cli and self.psk_thread_cli.isalive():
            LoggerWpa.debug("Stopping psk pexpect spawn")
            self.psk_thread_cli.sendline("quit")
            self.psk_thread_cli.close(True)
        LoggerWpa.debug("Stopping wpa process")
        if self.wpa_supplicant_process and self.wpa_supplicant_process.poll() is None:
            self.wpa_supplicant_process.terminate()
            self.kill_wpa()
        # reset
        self.clear_status_change_listeners()
        self.time_start = 0
        self.time_scan = 0
        LoggerWpa.debug("Wpa stopped")

    def scan_contains_wii_u(self, scan_results):
        """
        Check if string contains Wii U SSID
        :param scan_results: string
        :return: boolean
        """
        for line in scan_results.splitlines():
            if self.wiiu_ap_regex.match(line):
                return True
        return False

    def scan_is_empty(self, scan_results):
        """
        Check if the scan has no MAC addresses
        :param scan_results: string
        :return: boolean
        """
        for line in scan_results.split("\n"):
            if self.mac_addr_regex.match(line):
                return False
        return True

    def get_psk(self, conf_path, interface, code):
        """
        Starts a thread to connect and attempt to obtain a Wii U's PSK
        Status:
          FAILED_START: there was an error attempting to parse CLI output - exception is logged
          NOT_FOUND: wpa_supplicant_drc did not find any Wii U APs
          TERMINATED: wpa_supplicant_drc could not authenticate with any SSIDs
          DISCONNECTED: auth details were saved
        :return: None
        """
        self.connect(conf_path, interface, status_check=False)
        self.psk_thread = Thread(target=self.get_psk_thread, kwargs={"code": code}, name="PSK Thread")
        self.psk_thread.start()

    def get_psk_thread(self, code):
        """
        Thread that attempts to authenticate with a Wii U. Updates status
        :param code: WPS PIN
        :return: None
        """
        try:
            LoggerWpa.debug("CLI expect starting")
            self.psk_thread_cli = pexpect.spawn("wpa_cli_drc -p /var/run/wpa_supplicant_drc")
            LoggerWpa.debug("CLI expect Waiting for init")
            self.psk_thread_cli.expect("Interactive mode")
            # Scan for Wii U SSIDs
            scan_tries = 5
            wii_u_bssids = []
            while self.running and scan_tries > 0:
                self.psk_thread_cli.sendline("scan")
                LoggerWpa.debug("CLI expect waiting for scan results available event")
                self.psk_thread_cli.expect("<3>CTRL-EVENT-SCAN-RESULTS", timeout=60)
                self.psk_thread_cli.sendline("scan_results")
                LoggerWpa.debug("CLI expect waiting for scan results")
                self.psk_thread_cli.expect("bssid / frequency / signal level / flags / ssid")
                for line in range(0, 100):  # up to 100 APs
                    try:
                        self.psk_thread_cli.expect(self.mac_addr_regex.pattern, timeout=1)
                    except pexpect.TIMEOUT:
                        break
                scan_results = self.psk_thread_cli.before.decode()
                LoggerWpa.finer("CLI expect - scan results: %s", scan_results)
                for line in scan_results.splitlines():
                    if self.wiiu_ap_regex.match(line):
                        wii_u_bssids.append(line.split()[0])
                if len(wii_u_bssids) == 0:
                    scan_tries -= 1
                else:
                    scan_tries = 0
            # Check for found Wii U ssids
            if len(wii_u_bssids) == 0:
                LoggerWpa.debug("No Wii U SSIDs found")
                self.set_status(self.NOT_FOUND)
                return
            # attempt to pair with any wii u bssid
            for bssid in wii_u_bssids:
                self.psk_thread_cli.sendline("wps_pin %s %s" % (bssid, code + "5678"))
                LoggerWpa.debug("CLI expect waiting for wps_pin input confirmation")
                self.psk_thread_cli.expect(code + "5678")
                LoggerWpa.debug("CLI expect waiting for authentication")
                try:
                    self.psk_thread_cli.expect("<3>WPS-CRED-RECEIVED", timeout=60)
                    # save conf
                    LoggerWpa.debug("PSK obtained")
                    # Save to temp config before reading from it
                    self.psk_thread_cli.sendline("save_config")
                    self.psk_thread_cli.expect("OK", timeout=5)
                    self.save_connect_conf(bssid)
                    self.set_status(self.DISCONNECTED)
                    return
                except pexpect.TIMEOUT:
                    LoggerWpa.debug("CLI expect BSSID auth failed")
                    self.psk_thread_cli.sendline("reconnect")
                    self.psk_thread_cli.expect("OK")
        # Timed out
        except pexpect.TIMEOUT as e:
            LoggerWpa.debug("PSK get attempt ended with an error.")
            LoggerWpa.exception(e)
            self.set_status(self.FAILED_START)
        # Failed to authenticate
        LoggerWpa.debug("Could not authenticate with any SSIDs")
        self.set_status(self.TERMINATED)

    @staticmethod
    def save_connect_conf(bssid):
        """
        Modify the temp get_psk configuration to be a connect configurraton and save it to
         ~/.drc-sim/connect_to_wii_u.conf.
        :param bssid: Wii U BSSID
        :return: None
        """
        LoggerWpa.debug("Saving connection config")
        # add additional connect information to config
        conf = open(constants.PATH_CONF_CONNECT_TMP, "r")
        lines = conf.readlines()
        conf.close()
        for line in lines:
            if "update_config=1" in line:
                lines.insert(lines.index(line) + 1, "ap_scan=1\n")
                break
        for line in lines:
            if "network={" in line:
                lines.insert(lines.index(line) + 1, "\tscan_ssid=1\n")
                lines.insert(lines.index(line) + 2, "\tbssid=" + bssid + "\n")
                break
        save_conf = open(constants.PATH_CONF_CONNECT, "w")
        save_conf.writelines(lines)
        save_conf.close()
        LoggerWpa.info("Authenticated with the Wii U")
