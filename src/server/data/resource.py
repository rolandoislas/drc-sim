import os

import pkg_resources
import sys

from src.server.util.logging.logger import Logger


def join(*args):
    return os.path.join(*args)


class Resource:
    def __init__(self, in_path):
        pre = "resources/"
        Logger.debug("Loading resource \"%s\"", join(pre, in_path))
        current_dir = os.path.dirname(__file__).split(os.sep)
        # Check local files first
        file_path = "/"
        if len(current_dir) >= 3:
            for path in range(0, len(current_dir) - 3):
                file_path = join(file_path, current_dir[path])
            file_path = join(file_path, pre, in_path)
            if os.path.exists(file_path):
                try:
                    with open(file_path) as f:
                        self.resource = f.read()
                except UnicodeDecodeError:
                    Logger.debug("Opening resource as binary.")
                    with open(file_path, "rb") as f:
                        self.resource = f.read()
                Logger.extra("Found resource in local resource directory.")
                return
        # Check /usr/local - pip installs to here
        file_path = "/usr/local/resources/" + in_path
        if os.path.exists(file_path):
            try:
                with open(file_path) as f:
                    self.resource = f.read()
            except UnicodeDecodeError:
                Logger.debug("Opening resource as binary.")
                with open(file_path, "rb") as f:
                    self.resource = f.read()
                Logger.extra("Found resource in /usr/local/ resource directory.")
                return
        # Attempt to get from package - setup.py installs here
        try:
            self.resource = pkg_resources.resource_string(pkg_resources.Requirement.parse("drcsim"), join(pre, in_path))
            Logger.extra("Found resource in package.")
        except FileNotFoundError:
            Logger.throw("Could not find resource: %s" % join(pre, in_path))
            sys.exit()
