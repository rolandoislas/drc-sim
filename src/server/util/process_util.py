import subprocess

import errno

from src.server.util.logging.logger import Logger


class ProcessUtil:
    def __init__(self):
        pass

    @classmethod
    def get_output(cls, command, silent=False):
        """
        Wraps a subprocess.check_output call. Checks for process errors and command not found errors.
        :param silent: If silent is true the command will not be logged
        :param command: array of strings - same as check_output
        :return: string of output, error, or None if the command is not found
        """
        try:
            if not silent:
                Logger.extra("Attempting to execute command %s", command)
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        except OSError as e:
            output = ""
            if e.errno == errno.ENOENT:
                Logger.warn("\"%s\" may not be installed", command[0])
            else:
                Logger.exception(e)
            cls.log_failed_command(command)
        except subprocess.CalledProcessError as e:
            output = e.output
            cls.log_failed_command(command, output.strip())
        Logger.verbose("Command \"%s\" output %s", command, output)
        return output

    @classmethod
    def call(cls, command):
        """
        Same as subprocess.call but outputs to logger
        :param command: string array - same as call
        :return: None
        """
        cls.get_output(command)

    @classmethod
    def log_failed_command(cls, command, output=None):
        Logger.extra("Failed to execute command \"%s\" and got output \"%s\"", command, output)
