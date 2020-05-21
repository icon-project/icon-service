import argparse
from collections import OrderedDict
from typing import List

from tools.precommit_converter.convert_engine import ConvertEngine


def extract_key_value_from_line(line: str):
    """
    Extract key, value from the precommit text file
    If the format change, should fix this method
    :param line:
    :return:
    """
    sliced_str: list = line.split(" ")
    for i, string in enumerate(sliced_str):
        if string == "-":
            key = sliced_str[i - 1]
            value = sliced_str[i + 1]
            if value[-1] == ",":
                value = value[:len(value) - 1]
            return bytes.fromhex(key), bytes.fromhex(value)
    else:
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Parse the precommit')
    # parser.add_argument('precommit_file', type=str, default=None
    #                     help='file name')
    # args = parser.parse_args()
    # file_name: str = args.precommit_file

    # Open the file
    convert_engine = ConvertEngine()

    batches: dict = OrderedDict()
    # Todo: temporal logic for Test
    with open("../precommit.txt", "rt") as f:
        # Collect the key, values
        lines: List[str] = f.readlines()
        for i, line in enumerate(lines):
            key, value = extract_key_value_from_line(line)
            if key is not None:
                batches[key] = value
                # Iter key, value and convert hex string -> bytes -> object
                converted_key, converted_value = convert_engine.convert(key, value)
                print(f"----------{i}-----------\n"
                      f"Key  : {converted_key} \n"
                      f"Value: {converted_value}")


if __name__ == "__main__":
    main()
