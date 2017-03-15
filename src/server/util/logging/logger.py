import logging
import os
import shutil
import sys

from src.server.data import constants


class Logger:
    level = logging.INFO
    EXTRA = logging.DEBUG - 1
    FINER = logging.DEBUG - 2
    VERBOSE = logging.DEBUG - 3
    logger = logging.getLogger("drcsim")
    consoleHandler = None
    fileHandler = None

    def __init__(self, name=None):
        if not Logger.logger.handlers:
            # Logger
            if name:
                Logger.logger = logging.getLogger(name)
            # Console output
            Logger.consoleHandler = logging.StreamHandler()
            Logger.consoleHandler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s:%(name)s %(message)s"))
            Logger.logger.addHandler(Logger.consoleHandler)
            # File output
            log_path = os.path.join(constants.LOG_PATH, Logger.logger.name + ".log")
            if not os.path.exists(constants.LOG_PATH):
                os.mkdir(constants.LOG_PATH)
            if os.path.exists(log_path):
                shutil.copyfile(log_path, log_path.replace(".log", "-1.log"))
                os.remove(log_path)
            Logger.fileHandler = logging.FileHandler(log_path)
            Logger.fileHandler.setFormatter(Logger.consoleHandler.formatter)
            Logger.logger.addHandler(Logger.fileHandler)
        # Level names
        logging.addLevelName(Logger.EXTRA, "EXTRA")
        logging.addLevelName(Logger.FINER, "FINER")
        logging.addLevelName(Logger.VERBOSE, "VERBOSE")

    @classmethod
    def info(cls, message, *args):
        cls.logger.info(message, *args)

    @classmethod
    def debug(cls, message, *args):
        cls.logger.debug(message, *args)

    @classmethod
    def extra(cls, message, *args):
        cls.logger.log(cls.EXTRA, message, *args)

    @classmethod
    def verbose(cls, message, *args):
        cls.logger.log(cls.VERBOSE, message, *args)

    @classmethod
    def set_level(cls, level):
        cls.level = level
        cls.logger.setLevel(cls.level)
        cls.consoleHandler.setLevel(cls.level)

    @classmethod
    def warn(cls, message, *args):
        cls.logger.warning(message, *args)

    @classmethod
    def throw(cls, exception, message=None, *args):
        cls.logger.error("=" * 50 + "[Crash]" + "=" * 50)
        if message:
            cls.logger.error(message, *args)
        if isinstance(exception, Exception):
            cls.logger.exception(exception)
        else:
            cls.logger.error(exception)
        cls.logger.error("=" * 50 + "[Crash]" + "=" * 50)
        sys.exit(1)

    @classmethod
    def finer(cls, message, *args):
        cls.logger.log(cls.FINER, message, *args)

    @classmethod
    def exception(cls, exception, *args):
        cls.logger.log(cls.EXTRA, exception, *args, exc_info=1)
