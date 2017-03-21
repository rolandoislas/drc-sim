import argparse

import sys


class Args:
    args = None

    def __init__(self):
        pass

    @staticmethod
    def parse_args():
        arg_parser = argparse.ArgumentParser(description="Drc-sim backend decodes packets and serves clients")
        # Logging
        arg_parser.add_argument("-d", "--debug", action="store_const", const=True, default=False,
                                help="debug output")
        arg_parser.add_argument("-e", "--extra", action="store_const", const=True, default=False,
                                help="extra debug output")
        arg_parser.add_argument("-f", "--finer", action="store_const", const=True, default=False,
                                help="finer debug output")
        arg_parser.add_argument("-v", "--verbose", action="store_const", const=True, default=False,
                                help="verbose debug output")
        arg_parser.add_argument("-c", "--cli", action="store_const", const=True, default=False,
                                help="disable gui")
        # CLI
        args = ["-c", "--cli", "-h", "--help"]
        found = False
        for arg in args:
            if arg in sys.argv:
                found = True
        if found:
            subparsers = arg_parser.add_subparsers()
            # Run Server
            run_server = subparsers.add_parser("run_server")
            run_server.add_argument("wii_u_interface", type=str)
            run_server.add_argument("normal_interface", type=str)
            # Get Key
            get_key = subparsers.add_parser("get_key")
            get_key.add_argument("wii_u_interface", type=str)
            get_key.add_argument("wps_pin", type=str)
        Args.args = arg_parser.parse_args()
        # Add sub arguments
        Args.args.run_server = False
        Args.args.get_key = False
        if "run_server" in sys.argv:
            Args.args.run_server = True
        elif "get_key" in sys.argv:
            Args.args.get_key = True
