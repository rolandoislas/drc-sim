import argparse


class Args:
    args = None

    def __init__(self):
        pass

    @staticmethod
    def parse_args():
        arg_parser = argparse.ArgumentParser(description="Drc-sim backend decodes packets and serves clients")
        arg_parser.add_argument("-d", "--debug", action="store_const", const=True, default=False,
                                help="debug output")
        arg_parser.add_argument("-e", "--extra", action="store_const", const=True, default=False,
                                help="extra debug output")
        arg_parser.add_argument("-f", "--finer", action="store_const", const=True, default=False,
                                help="finer debug output")
        arg_parser.add_argument("-v", "--verbose", action="store_const", const=True, default=False,
                                help="verbose debug output")
        Args.args = arg_parser.parse_args()
