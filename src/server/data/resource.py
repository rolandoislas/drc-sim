import os

import pkg_resources

from src.server.util.logging.logger import Logger


def join(*args):
    return os.path.join(*args)


class Resource:
    def __init__(self, in_path):
        pre = "resources/"
        Logger.debug("Loading resource \"%s\"", join(pre, in_path))
        self.resource = pkg_resources.resource_string(pkg_resources.Requirement.parse("drcsim"), join(pre, in_path))
