from typing import List, Tuple

from tools.precommit_converter.utils import extract_key_values_from_file
from tools.precommit_converter.convert_engine import ConvertEngine, ConvertedKeyValues
from tools.precommit_converter.printer import Printer


class Convert:
    NAME = "convert"
    HELP_MSG = "Convert hex string data to human readable"

    @classmethod
    def _get_parents(cls, common_parser) -> list:
        parents: list = []
        if common_parser is not None:
            parents.append(common_parser)
        return parents

    @classmethod
    def add_command(cls, sub_parser, *, common_parser=None):
        parents: list = cls._get_parents(common_parser)
        calculate_parser = sub_parser.add_parser(cls.NAME, parents=parents, help=Convert.HELP_MSG)
        calculate_parser.add_argument("path", type=str, help="Precommit data file path")
        calculate_parser.set_defaults(func=cls.run)

    @classmethod
    def run(cls, args):
        file_path: str = args.path
        convert_engine = ConvertEngine()
        printer = Printer()

        key_values: List[Tuple[bytes, bytes]] = extract_key_values_from_file(file_path)
        converted_key_values: List['ConvertedKeyValues'] = convert_engine.convert(key_values)
        printer.print(converted_key_values)
