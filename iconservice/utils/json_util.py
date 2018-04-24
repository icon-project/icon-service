from ..base.address import Address


def convert_dict_values(json_dict: dict) -> dict:
    """Convert json into appropriate format.

    :param json_dict:
    :return:
    """
    json_dictionary = {}

    for key in json_dict:
        if isinstance(json_dict[key], dict):
            json_dictionary[key] = convert_dict_values(json_dict[key])
        else:
            json_dictionary[key] = convert_value(json_dict[key])

    return json_dictionary


def convert_value(str_value_with_type: str):
    """Convert str value into specified type.

    :param str_value_with_type:
    example1: '123 -> int'
    example2: '[1,2,3] -> int_array'
    example3: '[True, False, False] -> bool_array'
    :return:
    """
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
        tmp_str_array = eval(value)
        return [int(a, 0) for a in tmp_str_array]
    elif specified_type == "bool_array":
        tmp_str_array = eval(value)
        return [string_to_bool(a) for a in tmp_str_array]
    elif specified_type == "string_array":
        return eval(value)
    elif specified_type == "address_array":
        tmp_str_array = _convert_into_str_array(value)
        return [Address(a[:2], bytes.fromhex(a[2:])) for a in tmp_str_array]
    else:
        raise Exception


def _convert_into_str_array(str_array: str) -> list:
    """Used inside convert_value function. This function will remove quotes, double quotes and space from the string.

    :param str_array:
    :return:
    """
    string_array = str_array[1:-1]
    return string_array.replace('"', '').replace("'", '').replace(' ', '').split(",")


def string_to_bool(str_bool: str) -> bool:
    """Convert str_bool to bool value. This function will returns False When argument is 'False'

    :param str_bool:
    :return:
    """
    if bool(str_bool) is False or str_bool == "False":
        return False
    return True
