import logging
import os
import shutil

from src.server.data import constants
from src.server.util.os_util import OsUtil


class Logger:
    level = logging.INFO
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    EXTRA = logging.DEBUG - 1
    FINER = logging.DEBUG - 2
    VERBOSE = logging.DEBUG - 3
    logger = logging.getLogger("drcsim")
    console_handler = None
    file_handler = None

    def __init__(self, name=None):
        if not Logger.console_handler or not Logger.file_handler:
            Logger.logger, Logger.console_handler, Logger.file_handler = self.create_logger(name)
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
        cls.console_handler.setLevel(cls.level)
        cls.file_handler.setLevel(cls.level)

    @classmethod
    def warn(cls, message, *args):
        cls.logger.warning(message, *args)

    @classmethod
    def throw(cls, exception, message=None, *args):
        cls.logger.error(str("=" * 10 + " [ CRASH ] " + "=" * 10))
        OsUtil.log_info(cls.logger)
        if message:
            cls.logger.error(message, *args)
        if isinstance(exception, Exception):
            cls.logger.exception(exception)
        else:
            cls.logger.error(exception)
        cls.logger.error(str("=" * 10 + " [ CRASH ] " + "=" * 10))
        if cls != Logger:
            raise exception

    @classmethod
    def finer(cls, message, *args):
        cls.logger.log(cls.FINER, message, *args)

    @classmethod
    def exception(cls, exception, *args):
        cls.logger.log(cls.EXTRA, exception, *args, exc_info=1)

    @classmethod
    def get_level(cls):
        return cls.level

    @staticmethod
    def create_logger(name):
        logger = logging.getLogger(name)
        format_str = "%(asctime)s %(levelname)s:%(name)s %(message)s"
        # Console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(console_handler)
        # File output
        log_path = os.path.join(constants.PATH_LOG_DIR, logger.name + ".log")
        if not os.path.exists(constants.PATH_ROOT):
            os.mkdir(constants.PATH_ROOT)
        if not os.path.exists(constants.PATH_LOG_DIR):
            os.mkdir(constants.PATH_LOG_DIR)
        if os.path.exists(log_path):
            shutil.copyfile(log_path, log_path.replace(".log", "-1.log"))
            os.remove(log_path)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(file_handler)
        return logger, console_handler, file_handler

Logger("drcsim")
