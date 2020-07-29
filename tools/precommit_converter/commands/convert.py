from tools.precommit_converter.converter.convert_engine import ConvertEngine
from tools.precommit_converter.extractor.extractor import Extractor
from tools.precommit_converter.printer.printer import Printer


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
        verbose: bool = args.verbose
        file_path: str = args.path

        convert_engine = ConvertEngine()
        printer = Printer(verbose=verbose)

        icon_service_info, kvs = Extractor.extract(file_path)
        convert_engine.set_converted_key_values(kvs)
        printer.print(icon_service_info, kvs)
