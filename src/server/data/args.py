import argparse


class Args:
    args = None

    def __init__(self):
        pass

    @staticmethod
    def parse_args():
        arg_parser = argparse.ArgumentParser(description="Drc-sim backend decodes packets and serves clients")
        arg_parser.add_argument("--debug", action="store_const", const=True, default=False,
                                help="debug output")
        Args.args = arg_parser.parse_args()
