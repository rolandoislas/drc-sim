from src.server.data import constants
from src.server.data.config_server import ConfigServer
from src.server.util.logging.logger_wpa import LoggerWpa
from src.server.data.args import Args
from src.server.ui.cli.cli_main import CliMain
from src.server.ui.gui.gui_main import GuiMain
from src.server.util.logging.logger import Logger
from src.server.util.logging.logger_backend import LoggerBackend
from src.server.util.logging.logger_cli import LoggerCli
from src.server.util.logging.logger_gui import LoggerGui
from src.server.util.os_util import OsUtil


def init_loggers():
    loggers = (Logger, LoggerBackend, LoggerGui, LoggerCli, LoggerWpa)
    for logger in loggers:
        if Args.args.debug:
            logger.set_level(Logger.DEBUG)
        elif Args.args.extra:
            logger.set_level(Logger.EXTRA)
        elif Args.args.finer:
            logger.set_level(Logger.FINER)
        elif Args.args.verbose:
            logger.set_level(Logger.VERBOSE)
        else:
            logger.set_level(Logger.INFO)


def start():
    ui = None
    try:
        if Args.args.cli:
            Logger.info("Enabling CLI")
            ui = CliMain()
        else:
            Logger.info("Enabling GUI")
            ui = GuiMain()
        ui.start()
    except KeyboardInterrupt:
        if ui:
            ui.stop()
    except Exception, e:
        if ui:
            ui.stop()
        Logger.throw(e)
    Logger.info("Exiting")


def log_level():
    # Logger info
    Logger.debug("Debug logging enabled")
    Logger.extra("Extra debug logging enabled")
    Logger.finer("Finer debug logging enabled")
    Logger.verbose("Verbose logging enabled")
    if LoggerWpa.get_level() <= Logger.FINER:
        LoggerWpa.warn("At this log level SSIDs are logged!")


def main():
    Args.parse_args()
    ConfigServer.load()
    ConfigServer.save()
    init_loggers()
    Logger.info("Initializing drc-sim-backend")
    Logger.info("Using \"%s\" as home folder.", constants.PATH_ROOT)
    log_level()
    OsUtil.log_info(Logger)
    start()


if __name__ == '__main__':
    main()
