import argparse
from argparse import ArgumentParser

from tools.precommit_converter.commands.convert import Convert
from tools.precommit_converter.commands.diff import Diff


def get_parser() -> 'ArgumentParser':
    parser = argparse.ArgumentParser(prog="converter", description="Precommit data converter")
    common_parser = _get_common_parser()
    _set_sub_parser(parser, common_parser)
    return parser


def _get_common_parser() -> 'ArgumentParser':
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("-v", "--verbose",
                               dest="verbose",
                               help="Print key value with primitive",
                               action='store_true',
                               default=False)

    return common_parser


def _set_sub_parser(parser, common_parser):
    sub_parser = parser.add_subparsers(description="", help="")
    Convert.add_command(sub_parser, common_parser=common_parser)
