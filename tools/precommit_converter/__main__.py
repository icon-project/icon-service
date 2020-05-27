import sys

from tools.precommit_converter.commands import get_parser

SUCCESS_CODE = 0
COMMAND_LINE_SYNTAX_ERROR = 1


def main():
    parser = get_parser()
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        return COMMAND_LINE_SYNTAX_ERROR

    try:
        print(args)
        args.func(args)
    except Exception as e:
        return e

    return SUCCESS_CODE


if __name__ == "__main__":
    sys.exit(main())
