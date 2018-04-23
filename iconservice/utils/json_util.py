from ..base.address import Address


def convert_dict_values(json_dict: dict) -> dict:
    json_dictionary = {}

    for key in json_dict:
        if isinstance(json_dict[key], dict):
            json_dictionary[key] = convert_dict_values(json_dict[key])
        else:
            json_dictionary[key] = convert_value(json_dict[key])

    return json_dictionary


def convert_value(str_value_with_type: str):
    specified_type = str_value_with_type.split(" -> ")[-1]
    separator_index = str_value_with_type.rfind(" -> ")
    value = str_value_with_type[:separator_index]
    if specified_type == "int":
        return int(value, 0)
    elif specified_type == "string":
        return value
    elif specified_type == "bool":
        return bool(value)
    elif specified_type == "address":
        return Address(value[:2], bytes.fromhex(value[2:]))
    elif specified_type == "int_array":
        tmp_str_array = _convert_into_str_array(value)
        return [int(a, 0) for a in tmp_str_array.split(",")]
    elif specified_type == "bool_array":
        tmp_str_array = _convert_into_str_array(value)
        return [string_to_bool(a) for a in tmp_str_array.split(",")]
    elif specified_type == "string_array":
        return get_str_array_from_str(value[1:-1])
    elif specified_type == "address_array":
        tmp_str_array = _convert_into_str_array(value)
        return [Address(a[:2], bytes.fromhex(a[2:])) for a in tmp_str_array.split(",")]
    else:
        raise Exception


def _convert_into_str_array(str_array: str) -> str:
    return str_array[1:-1].replace('"', '').replace("'", '').replace(' ', '')


def string_to_bool(str_bool: str) -> bool:
    if bool(str_bool) is False or str_bool == "False":
        return False
    return True


def get_str_array_from_str(string: str):
    quotes_count = 0
    quotes = string[0]
    str_array = []
    element = ''
    for index, char in enumerate(string, 1):
        if char == quotes:
            quotes_count += 1
        else:
            if quotes_count == 0:
                continue
            element += char
        if quotes_count == 2:
            quotes_count = 0
            str_array.append(element)
            element = ''

    return str_array
