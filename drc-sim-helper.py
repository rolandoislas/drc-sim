# coding=utf-8
import argparse
import curses
import curses.textpad
import locale
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from distutils import spawn

import netifaces as netifaces
import pkg_resources


class DrcSimHelper:
    def __init__(self):
        if os.getuid() != 0:
            raise SystemExit("This script needs to be run as root.")
        self.height = None
        self.args = None
        self.active_command = None
        self.textbox = None
        self.window_main = None
        self.input_thread = None
        self.input_queue = multiprocessing.Queue()
        self.title = "drc-sim-helper"
        self.log_path = os.path.expanduser("~/.drc-sim/")
        locale.setlocale(locale.LC_ALL, "")
        self.parse_args()
        curses.wrapper(self.start)

    def parse_args(self):
        arg_parser = argparse.ArgumentParser(description="Helper script for connecting to the Wii U.",
                                             prefix_chars="- ")
        arg_parser.add_argument("--all-interfaces", action="store_const",
                                const=True, default=False, help="show all interfaces instead of only the Wii U "
                                                                "compatible")
        arg_parser.add_argument("--log", action="store_const", const=True, default=False,
                                help="log output of wpa_supplicant_drc and the backend")
        if "run_server" in sys.argv:
            subparsers = arg_parser.add_subparsers()
            # run_server
            run_server = subparsers.add_parser("run_server")
            run_server.add_argument("wiiu_interface", type=str)
            run_server.add_argument("normal_interface", type=str)
            # add to input queue to trigger command parsing
            self.input_queue.put("")
        else:
            arg_parser.add_argument(" run_server", dest="...", help="connects to the wii u and runs drc-sim-backend ("
                                                                    "needs auth details)")
        self.args = arg_parser.parse_args()
        self.args.run_server = "run_server" in sys.argv

    def start(self, screen):
        height, width = screen.getmaxyx()
        self.height = height
        # title
        screen.addstr(0, width / 2 - len(self.title) / 2, self.title)
        # command prompt symbol
        screen.addstr(height - 1, 0, "$ ")
        screen.refresh()
        # main display
        self.window_main = curses.newwin(height - 2, width, 1, 0)
        # input
        window_input = curses.newwin(1, width - 2, height - 1, 2)
        self.textbox = curses.textpad.Textbox(window_input)

        self.input_thread = InputThread(self.input_queue, self.textbox)
        self.input_thread.start()

        self.set_command(CommandHelp)
        try:
            while True:
                self.parse_queue()
                self.active_command.update()
                time.sleep(0.01)
        except Exception as e:
            self.stop(e)

    def parse_queue(self):
        if self.input_queue.empty():
            return
        input_text = self.input_queue.get(1).strip()
        self.input_queue.empty()
        # global
        if input_text == "quit" or input_text == "exit":
            self.stop()
        # active command
        new_command = self.active_command.parse_command(input_text)
        if new_command:
            self.set_command(new_command)

    def stop(self, message=None):
        self.active_command.stop()
        self.input_thread.terminate()
        if isinstance(message, Exception):
            type_, value_, traceback_ = sys.exc_info()
            raise SystemExit("".join(traceback.format_tb(traceback_)) + type_.__name__ + "\n" + str(value_))
        else:
            raise SystemExit(message)

    def set_command(self, command):
        if self.active_command:
            self.active_command.stop()
        self.active_command = command(self, self.window_main, self.textbox)


class InputThread(multiprocessing.Process):
    def __init__(self, queue, textbox):
        super(InputThread, self).__init__()
        self.queue = queue
        self.textbox = textbox

    def run(self):
        while True:
            try:
                text = self.textbox.edit()
            except KeyboardInterrupt:
                break
            self.queue.put(text)
            self.textbox.win.erase()


class Command:
    def __init__(self, parent, window_main, textbox):
        self.parent = parent
        self.window_main = window_main
        self.textbox = textbox
        self.show_main()

    def parse_command(self, command):
        pass

    def show_main(self):
        pass

    def stop(self):
        pass

    def update(self):
        pass

    def clear(self):
        self.window_main.clear()
        self.window_main.refresh()
        self.textbox.win.refresh()

    def write(self, y, x, text):
        self.window_main.addstr(y, x, text)
        self.window_main.refresh()
        self.textbox.win.refresh()

    def prompt_user_input_choice(self, choices, prompt):
        self.clear()
        for y in range(0, len(prompt)):
            self.write(y, 0, prompt[y])
        for y in range(0, len(choices)):
            self.write(y + len(prompt) + 1, 0, str(y + 1) + ") " + str(choices[y]))

    def prompt_user_input(self, prompt):
        self.clear()
        for y in range(0, len(prompt)):
            self.write(y, 0, prompt[y])


class CommandHelp(Command):
    def parse_command(self, command):
        if command == "help":
            self.parent.set_command(CommandHelp)
        elif command == "get_key":
            self.parent.set_command(CommandGetKey)
        elif command == "run_server" or self.parent.args.run_server:
            self.parent.set_command(CommandRunServer)
        elif command == "route":
            self.parent.set_command(CommandRoute)

    def show_main(self):
        self.clear()
        self.write(0, 0, "Help")
        self.write(2, 0, "Commands:")

        self.write(3, 0, "help  show this help screen")
        self.write(4, 0, "quit  exit the program")
        self.write(5, 0, "get_key   obtain the ssid, bssid, and psk from the wii u")
        self.write(6, 0, "run_server    connects to the wii u and runs drc-sim-backend (needs auth details)")
        self.write(7, 0, "route    adds network routes (dev)")


class NetworkCommand(Command):
    def __init__(self, parent, window_main, textbox, forward_method):
        Command.__init__(self, parent, window_main, textbox)
        self.forward_method = forward_method
        # process
        self.wpa_supplicant_process = None
        # input bool
        self.requesting_interface_wii_input = False
        self.requesting_networkmanager_unmanage_input = False
        self.requesting_interface_normal_input = False
        # interfaces
        self.interfaces_wiiu = None
        self.interface_wiiu = None
        self.interfaces_normal = None
        self.interface_normal = None
        # static
        self.nm_conf = "/etc/NetworkManager/NetworkManager.conf"
        self.tmp_conf_psk = "/tmp/drc-sim/get_psk.conf"
        self.conf_psk = os.path.expanduser("~/.drc-sim/connect_to_wii_u.conf")
        # start
        self.prompt_wiiu_interface()

    def parse_command(self, command):
        # check which wiiu interface should be used
        if self.requesting_interface_wii_input:
            try:
                index = int(command)
                if 1 <= index <= len(self.interfaces_wiiu):
                    self.requesting_interface_wii_input = False
                    self.interface_wiiu = self.interfaces_wiiu[index - 1]
                    self.prompt_networkmanager_unmanage()
            except ValueError:
                pass
        # check which normal interface should be used
        elif self.requesting_interface_normal_input:
            try:
                index = int(command)
                if 1 <= index <= len(self.interfaces_normal):
                    self.requesting_interface_normal_input = False
                    self.interface_normal = self.interfaces_normal[index - 1]
                    self.forward_method()
            except ValueError:
                pass
        # check if interface should be set to unmanaged
        elif self.requesting_networkmanager_unmanage_input:
            try:
                index = int(command)
                if index == 1:  # yes
                    self.requesting_networkmanager_unmanage_input = False
                    self.set_interface_unmanaged()
                    self.forward_method()
                elif index == 2:  # no
                    self.requesting_networkmanager_unmanage_input = False
                    self.forward_method()
            except ValueError:
                pass

    def prompt_wiiu_interface(self):
        # Get interfaces
        self.interfaces_wiiu = InterfaceUtil.get_wiiu_compatible_interfaces() if not self.parent.args.all_interfaces \
            else InterfaceUtil.get_all_interfaces()
        if len(self.interfaces_wiiu) == 0 and not self.parent.args.run_server:
            self.parent.stop("No Wii U compatible wireless interfaces found. Add --all-interfaces to show all "
                             "interfaces.")
        # Check if arg passed in cli
        if hasattr(self.parent.args, "wiiu_interface"):
            for interface in InterfaceUtil.get_all_interfaces():
                if interface[0] == self.parent.args.wiiu_interface:
                    self.interface_wiiu = interface
            self.forward_method()
            return
        # Prompt
        self.prompt_user_input_choice(self.interfaces_wiiu,
                                      ["Select a wireless interface that will be used for connections to a Wii U."])
        self.requesting_interface_wii_input = True

    def prompt_normal_interface(self):
        # Get interfaces
        self.interfaces_normal = InterfaceUtil.get_all_interfaces()
        if self.interface_wiiu in self.interfaces_normal:
            self.interfaces_normal.remove(self.interface_wiiu)
        if len(self.interfaces_normal) == 0:
            self.parent.stop("No interfaces found.")
        # Check cli arg
        if hasattr(self.parent.args, "normal_interface"):
            for interface in self.interfaces_normal:
                if interface[0] == self.parent.args.normal_interface:
                    self.interface_normal = interface
            self.forward_method()
            return
        # Prompt
        self.prompt_user_input_choice(self.interfaces_normal,
                                      ["Select an interface that will be used for a standard network "
                                       "connection."])
        self.requesting_interface_normal_input = True

    def prompt_networkmanager_unmanage(self):
        # do not prompt user if they do not have network manager
        if not os.path.isfile(self.nm_conf):
            self.requesting_networkmanager_unmanage_input = False
            self.forward_method()
            return
        # do not prompt if device is already unmanaged
        conf = open(self.nm_conf)
        conf_data = conf.read()
        conf.close()
        if "mac:" + self.interface_wiiu[1] in conf_data:
            self.requesting_networkmanager_unmanage_input = False
            self.forward_method()
            return
        # prompt
        self.prompt_user_input_choice(["yes", "no"], ["Network Manager configuration found.",
                                                      "Would you like to set the interface '" + self.interface_wiiu[0] +
                                                      "' to unmanaged in network-manager's configuration file?",
                                                      "(You should only do this if the interface is not your primary "
                                                      "networking interface.)"])
        self.requesting_networkmanager_unmanage_input = True

    def set_interface_unmanaged(self):
        conf = open(self.nm_conf, "a")
        conf.writelines(["[keyfile]", "\nunmanaged-devices=mac:" + self.interface_wiiu[1]])
        conf.close()
        subprocess.call(["service", "network-manager", "restart"], stdout=open(os.devnull, "w"),
                        stderr=subprocess.STDOUT)

    def start_wpa_supplicant(self, conf):
        subprocess.call(["rfkill", "unblock", "wlan"], stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT)
        log = open(os.path.join(self.parent.log_path, "wpa_supplicant_drc.log"), "w") if self.parent.args.log else \
            open(os.devnull, "w")
        log.write("-" * 80 + "\nStarted wpa_supplicant_drc\n")
        self.wpa_supplicant_process = subprocess.Popen(["wpa_supplicant_drc", "-Dnl80211", "-i",
                                                        self.interface_wiiu[0], "-c", conf],
                                                       stdout=log, stderr=subprocess.STDOUT)

    def stop(self):
        if self.wpa_supplicant_process and not self.wpa_supplicant_process.poll():
            self.wpa_supplicant_process.terminate()
        self.kill_wpa()

    @staticmethod
    def kill_wpa():
        subprocess.call(["killall", "wpa_supplicant_drc"], stdout=open(os.devnull), stderr=subprocess.STDOUT)

    @staticmethod
    def wpa_cli(command):
        if isinstance(command, str):
            command = [command]
        try:
            process = subprocess.check_output(["wpa_cli_drc", "-p", "/var/run/wpa_supplicant_drc"] + command,
                                              stderr=subprocess.STDOUT)
            return process
        except subprocess.CalledProcessError:
            return ""


class CommandRunServer(NetworkCommand):
    def __init__(self, parent, window_main, textbox):
        # process
        self.drc_sim_backend_queue = multiprocessing.Queue()
        self.status_output_time = 0
        self.dead_process_time = None
        self.drc_sim_backend_process = None
        # network details
        self.ip = None
        self.subnet = None
        self.gateway = None

        NetworkCommand.__init__(self, parent, window_main, textbox, self.check_conf)

    def parse_command(self, command):
        NetworkCommand.parse_command(self, command)
        if command == "pypy":
            sys.executable = "pypy"
            self.drc_sim_backend_process.terminate()
            self.start_processes(True)

    def stop(self):
        NetworkCommand.stop(self)
        if self.drc_sim_backend_process and not self.drc_sim_backend_process.poll():
            self.drc_sim_backend_process.terminate()

    def update(self):
        # restart a terminated process
        if self.dead_process_time:
            # show status
            is_alive_wpa = self.wpa_supplicant_process.poll() is None
            is_alive_drc = self.drc_sim_backend_process.poll() is None
            if time.time() - self.status_output_time >= 1:
                self.status_output_time = time.time()
                self.window_main.addstr(0, 0, "Server status")
                wpa_status = self.wpa_cli("status")
                if "wpa_state=COMPLETED" in wpa_status:
                    wpa_status = "connected"
                elif "wpa_state=SCANNING" in wpa_status:
                    wpa_status = "connecting"
                else:
                    wpa_status = "unknown"
                self.window_main.addstr(2, 0, "Wii U Connection: " +
                                        (wpa_status if is_alive_wpa else "stopped") + " " * 20)
                self.window_main.addstr(3, 0, "Server: " +
                                        ("running" if is_alive_drc else "stopped") + " " * 20)
                self.window_main.addstr(5, 0, "Interface Wii U: " + self.interface_wiiu[0] + ", " +
                                        self.interface_wiiu[1])
                self.window_main.addstr(6, 0, "Interface Normal: " + self.interface_normal[0] + ", " +
                                        self.interface_normal[1] + ", " + self.ip)
                self.window_main.addstr(8, 0, "Logging: " + str(self.parent.args.log))
                if self.parent.args.log:
                    self.window_main.addstr(9, 0, "Log Path: " + self.parent.log_path)
                self.window_main.addstr(self.parent.height - 3, 0, "> ")
                self.window_main.refresh()
            # update time if running
            if is_alive_wpa and is_alive_drc:
                self.dead_process_time = time.time()
            # restart if process has been dead for a while
            if time.time() - self.dead_process_time >= 10:
                self.start_processes(True)

    def start_processes(self, restart=False):
        if not restart:
            self.stop()
        self.dead_process_time = time.time()
        self.clear()
        if self.wpa_supplicant_process is None or self.wpa_supplicant_process.poll():
            self.start_wpa_supplicant(self.conf_psk)
        self.add_route()
        if self.drc_sim_backend_process is None or self.drc_sim_backend_process.poll():
            self.start_drc_sim_backend()

    def start_drc_sim_backend(self):
        drc_sim_path = os.path.join(os.path.dirname(__file__), "drc-sim-backend.py")
        if not os.path.exists(drc_sim_path):
            drc_sim_path = os.path.abspath(spawn.find_executable("drc-sim-backend.py"))
        log = open(os.path.join(self.parent.log_path, "drc-sim-backend.log"), "w") if self.parent.args.log else \
            open(os.devnull, "w")
        log.write("-" * 80 + "\nStarted drc-sim-backend\n")
        command = [sys.executable, drc_sim_path]
        if self.parent.args.log:
            command.append("--debug")
        self.drc_sim_backend_process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)

    def add_route(self):
        wii_local_ip = "192.168.1.11"
        wii_subnet = "192.168.1.0/24"
        wii_gateway = "192.168.1.1"
        table_1 = "111"
        table_2 = "112"
        # Flush table in case they persisted
        subprocess.call(["ip", "route", "flush", "table", table_1], stdout=open(os.devnull), stderr=subprocess.STDOUT)
        subprocess.call(["ip", "route", "flush", "table", table_2], stdout=open(os.devnull), stderr=subprocess.STDOUT)
        # Flush the device
        subprocess.call(["ip", "addr", "flush", "dev", self.interface_wiiu[0]], stdout=open(os.devnull),
                        stderr=subprocess.STDOUT)
        for interface in self.interfaces_normal:
            if interface[0] != "lo":
                subprocess.call(["ip", "addr", "flush", "dev", interface[0]], stdout=open(os.devnull),
                                stderr=subprocess.STDOUT)
        # This creates two different routing tables, that we use based on the source-address.
        subprocess.check_call(["ip", "rule", "add", "from", self.ip, "table", table_1], stdout=open(os.devnull),
                              stderr=subprocess.STDOUT)
        subprocess.call(["ip", "rule", "add", "from", wii_local_ip, "table", table_2], stdout=open(os.devnull),
                        stderr=subprocess.STDOUT)
        # Assign an ip to the interface.
        subprocess.call(["ifconfig", self.interface_wiiu[0], wii_local_ip], stdout=open(os.devnull),
                        stderr=subprocess.STDOUT)
        # Configure first routing table
        subprocess.call(["ip", "route", "add", self.subnet, "dev", self.interface_normal[0],
                         "scope", "link", "table", table_1], stdout=open(os.devnull), stderr=subprocess.STDOUT)
        subprocess.call(["ip", "route", "add", "default", "via", self.gateway, "dev",
                         self.interface_normal[0], "table", table_1], stdout=open(os.devnull), stderr=subprocess.STDOUT)
        # Configure second routing table
        subprocess.call(["ip", "route", "add", wii_subnet, "dev", self.interface_wiiu[0], "scope",
                         "link", "table", table_2], stdout=open(os.devnull), stderr=subprocess.STDOUT)
        subprocess.call(["ip", "route", "add", "default", "via", wii_gateway, "dev",
                         self.interface_wiiu[0], "table", table_2], stdout=open(os.devnull), stderr=subprocess.STDOUT)
        # default route for the selection process of normal internet-traffic
        subprocess.call(["ip", "route", "add", "default", "scope", "global", "nexthop", "via",
                         self.gateway, "dev", self.interface_normal[0]], stdout=open(os.devnull),
                        stderr=subprocess.STDOUT)
        # Setup dhcp
        subprocess.call(["dhclient"], stdout=open(os.devnull), stderr=subprocess.STDOUT)

    def check_conf(self):
        # User needs auth details first
        if not os.path.isfile(self.conf_psk):
            self.parent.stop("No Wii U wireless authentication found at $dir. Try running \"get_key\"."
                             .replace("$dir", str(self.conf_psk)))
        # Prompt for normal NIC
        if not self.interface_normal:
            self.prompt_normal_interface()
            return
        # Calculate network details
        self.calulate_network_details()
        # start
        self.start_processes()

    def calulate_network_details(self):
        # Get interface ip
        self.ip = InterfaceUtil.get_ip(self.interface_normal[0])
        # Check if there is an ip
        if not self.ip:
            self.parent.stop("Selected normal interface is not connected to a network.")
        # Subnet and gateway
        ip_split = self.ip.split(".")
        ip_prefix = ".".join([ip_split[0], ip_split[1], ip_split[2]])
        self.subnet = ip_prefix + ".0/24"
        self.gateway = ip_prefix + ".1"


class CommandRoute(CommandRunServer):
    def stop(self):
        pass

    def start_processes(self, restart=False):
        self.add_route()
        self.parent.stop("Added route")


class CommandGetKey(NetworkCommand):
    def __init__(self, parent, window_main, textbox):
        NetworkCommand.__init__(self, parent, window_main, textbox, self.prompt_wps_pin)
        # wpa
        self.wpa_supplicant_process = None
        self.wps_pin = None
        self.bssid = None
        self.bssids = []
        # input bool
        self.requesting_wps_pin_input = False
        self.requesting_recan_input = False
        self.requesting_newpin_input = False

    def parse_command(self, command):
        NetworkCommand.parse_command(self, command)
        # get the wps pin from user
        if self.requesting_wps_pin_input:
            try:
                if len(command) == 4:
                    for char in command:
                        if int(char) < 0 or int(char) > 3:
                            return
                    self.requesting_wps_pin_input = False
                    self.wps_pin = command
                    self.get_key()
            except ValueError:
                pass
        # check if another scan should start
        elif self.requesting_recan_input:
            try:
                index = int(command)
                if index == 1:  # yes
                    self.get_key()
                elif index == 2:  # no
                    self.parent.stop("Failed to get Wii U authentication.")
            except ValueError:
                pass
        # check if user wants to enter new pin
        elif self.requesting_newpin_input:
            try:
                index = int(command)
                if index == 1:  # newpin
                    self.prompt_wps_pin()
                elif index == 2:  # exit
                    self.parent.stop("Failed to get Wii U authentication.")
            except ValueError:
                pass

    def prompt_wps_pin(self):
        self.prompt_user_input(["Input the Wii U's WPS key.",
                                "",
                                "Start gamepad sync mode on the Wii U.",
                                "The screen will show a spade/heart/diamond/clover in a certain order.",
                                "",
                                "Enter the key as a four numbers.",
                                "",
                                u"♠ (spade) = 0     ♥ (heart) = 1     ♦ (diamond) = 2     ♣ (clover) = 3"
                               .encode("utf-8"),
                                "",
                                u"Example: ♣♠♥♦ (clover, spade, heart, diamond) would equal 3012".encode("utf-8")])
        self.requesting_wps_pin_input = True

    def get_key(self):
        # Create temp config
        self.prompt_user_input(["Attempting to pair with the Wii U.", "This might take a few minutes."])
        tmp_dir = "/tmp/drc-sim/"
        conf_name = "get_psk.conf"
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        orig_conf = os.path.join(os.path.dirname(__file__), "resources/config/get_psk.conf")
        if not os.path.exists(orig_conf):
            orig_conf = pkg_resources.resource_string(pkg_resources.Requirement.parse("drcsim"),
                                                      "resources/config/get_psk.conf")
            conf_tmp = open(self.tmp_conf_psk, "w")
            conf_tmp.write(orig_conf)
            conf_tmp.close()
        else:
            shutil.copyfile(orig_conf, tmp_dir + conf_name)
        # Start wpa_supplicant
        self.stop()
        self.start_wpa_supplicant(tmp_dir + conf_name)
        # Start scan
        self.prompt_user_input(["Scanning WiFi networks."])
        tries = 0
        while "OK" not in self.wpa_cli("scan") and tries <= 10:
            tries += 1
            time.sleep(1)
        if tries > 10:
            self.parent.stop("Could not start AP scan.")
        # Parse scan results
        self.prompt_user_input(["Sorting networks."])
        tries = 0
        wiiu_ap = re.compile('^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})(\s*\d*\s*-*\d*\s*)(\[WPA2-PSK-CCMP\])?'
                             '(\[ESS\])(\s*)(WiiU|\\\\x00)(.+)$')  # \x00 is escaped (\\x00)
        while tries <= 10:
            for line in self.wpa_cli("scan_results").split("\n"):
                if wiiu_ap.match(line):
                    self.bssids.append(line.split()[0])
            if len(self.bssids) > 0:
                break
            tries += 1
            time.sleep(1)
        if tries > 10:
            self.prompt_user_input_choice(["yes", "no"],
                                          ["Wii U network not found. Scan again?", "",
                                           "- Your Wii U could be too far away.",
                                           "- Restart the Wii U and enter gampad pairing (sync) mode."])
            self.requesting_recan_input = True
            return
        # Try to authenticate
        self.prompt_user_input(["Attempting to connect."])
        tries = 0
        auth = False
        for bssid in self.bssids:
            self.bssid = bssid
            self.prompt_user_input(["Trying network " + str(self.bssids.index(bssid) + 1) + " of " +
                                    str(len(self.bssids))])
            self.wpa_cli(["wps_pin", bssid, self.wps_pin + "5678"])
            while tries <= 60:
                conf = open(tmp_dir + conf_name)
                lines = conf.readlines()
                conf.close()
                for line in lines:
                    if "network={" in line:
                        auth = True
                if auth:
                    break
                tries += 1
                time.sleep(1)
            if auth:
                break
        if tries > 60:
            self.prompt_user_input_choice(["Re-enter WPS PIN", "exit"],
                                          ["Could not connect to Wii U.", "",
                                           "- WPS PIN could be incorrect.",
                                           "- Restart the Wii U and enter gampad pairing (sync) mode."])
            self.requesting_newpin_input = True
            return
        # Save details
        self.save_key()

    def save_key(self):
        # Check the config path
        if not os.path.exists(os.path.expanduser("~/.drc-sim")):
            os.mkdir(os.path.expanduser("~/.drc-sim"))
        # add additional connect information to config
        conf = open(self.tmp_conf_psk, "r")
        lines = conf.readlines()
        conf.close()
        for line in lines:
            if "update_config=1" in line:
                lines.insert(lines.index(line) + 1, "ap_scan=1\n")
                break
        for line in lines:
            if "network={" in line:
                lines.insert(lines.index(line) + 1, " " * 8 + "scan_ssid=1\n")
                lines.insert(lines.index(line) + 2, " " * 8 + "bssid=" + self.bssid + "\n")
                break
        save_conf = open(self.conf_psk, "w")
        save_conf.writelines(lines)
        save_conf.close()
        self.parent.stop("Successfully saved Wii U authentication data.")


class InterfaceUtil:
    def __init__(self):
        pass

    @classmethod
    def get_wiiu_compatible_interfaces(cls):
        all_interfaces = cls.get_all_interfaces()
        compatible_interfaces = []
        for interface in all_interfaces:
            if cls.is_interface_wiiu_compatible(interface[0]):
                compatible_interfaces.append(interface)
        return compatible_interfaces

    @classmethod
    def get_all_interfaces(cls):
        interfaces = []
        for interface in netifaces.interfaces():
            interfaces.append([interface, cls.get_mac(interface)])
        return interfaces

    @classmethod
    def is_interface_wiiu_compatible(cls, interface):
        try:
            return "5." in subprocess.check_output(["iwlist", interface, "frequency"])
        except subprocess.CalledProcessError:
            return False

    @classmethod
    def get_ip(cls, interface):
        return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]["addr"]

    @classmethod
    def get_mac(cls, interface):
        return netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]["addr"]


if __name__ == '__main__':
    try:
        helper = DrcSimHelper()
    except KeyboardInterrupt:
        pass
