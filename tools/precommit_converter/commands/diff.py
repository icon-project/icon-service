class Diff(object):
    NAME = "diff"
    HELP_MSG = "Compare two precommit file"

    @classmethod
    def _get_parents(cls, common_parser) -> list:
        parents: list = []
        if common_parser is not None:
            parents.append(common_parser)
        return parents

    @classmethod
    def add_command(cls, sub_parser, *, common_parser=None):
        parents: list = cls._get_parents(common_parser)
        calculate_parser = sub_parser.add_parser(cls.NAME, parents=parents, help=Diff.HELP_MSG)
        calculate_parser.add_argument("path", nargs=2, type=str, help="precommit file path")
        calculate_parser.set_defaults(func=cls.run)

    @classmethod
    def run(cls, args):
        # Todo: TBD
        raise NotImplementedError()

