import sys
import traceback

from tools.precommit_converter.commands import get_parser

SUCCESS_CODE = 0
FAILURE_CODE = 1


def main():
    parser = get_parser()
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        return FAILURE_CODE

    try:
        args.func(args)
    except Exception as e:
        print(''.join(traceback.format_tb(e.__traceback__)), file=sys.stderr)
        print(e.args[0], file=sys.stderr)
        return FAILURE_CODE

    return SUCCESS_CODE


if __name__ == "__main__":
    sys.exit(main())
