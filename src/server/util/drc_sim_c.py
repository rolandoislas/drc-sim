import subprocess
from threading import Thread

import time

from src.server.data import constants
from src.server.util.logging.logger_backend import LoggerBackend
from src.server.util.process_util import ProcessUtil
from src.server.util.status_sending_thread import StatusSendingThread


class DrcSimC(StatusSendingThread):
    UNKNOWN = "UNKNOWN"
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"

    def __init__(self):
        """
        Helper for interacting with drc_sim_c.
        """
        super().__init__()
        self.running = False
        self.status = self.UNKNOWN
        self.drc_sim_c_process = None
        self.status_check_thread = None
        self.region = "none"

    def set_region(self, region):
        self.region = region

    def start(self):
        self.running = True
        self.kill_drc_sim_c()
        LoggerBackend.debug("Starting drc_sim_c")
        command = ["drc_sim_c", "-region", self.region]
        self.drc_sim_c_process = subprocess.Popen(command, stdout=open(constants.PATH_LOG_DRC_SIM_C, "w"),
                                                  stderr=subprocess.STDOUT)
        LoggerBackend.debug("Starting status check thread")
        self.status_check_thread = Thread(target=self.check_status, name="drc_sim_c Status Check Thread")
        self.status_check_thread.start()
        self.set_status(self.RUNNING)

    def check_status(self):
        while self.running:
            if self.drc_sim_c_process.poll():
                self.set_status(self.STOPPED)
            time.sleep(1)

    def stop(self):
        """
        Stops any background thread that is running
        :return: None
        """
        self.running = False
        LoggerBackend.debug("Stopping drc_sim_c")
        if self.drc_sim_c_process and self.drc_sim_c_process.poll() is None:
            self.drc_sim_c_process.terminate()
            self.kill_drc_sim_c()
        # reset
        self.clear_status_change_listeners()
        LoggerBackend.debug("Stopped drc_sim_c")

    @staticmethod
    def kill_drc_sim_c():
        ProcessUtil.call(["killall", "drc_sim_c"])
