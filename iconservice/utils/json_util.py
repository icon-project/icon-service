from ..base.address import Address

type_info = {
    "type_table": {
        "from": "address",
        "to": "address",
        "value": "int",
        "values": "int[]",
        "signature": "string",
        "addresses": "address[]",
        "success": "bool",
        "boolList": "bool[]",
        "stringList": "string[]"
        # "balances": "dict[address:int]"
    },
    "two_depth_json_type": {
        "address1": "address",
        "address2": "address",
        "value": "int",
        "int_val": 'int',
        "str_val": "string",
        "data": {
            "data-param1": "address",
            "data-param2": "address",
            "data-param3": "int",
            "data-param4": 'int',
            "data-param5": "string",
            "data-param6": "address[]"
        }
    }
}
CONST_INT = "int"
CONST_STRING = "string"
CONST_BOOL = "bool"
CONST_ADDRESS = "address"
CONST_INT_ARRAY = "int[]"
CONST_STRING_ARRAY = "string[]"
CONST_BOOL_ARRAY = "bool[]"
CONST_ADDRESS_ARRAY = "address[]"


def convert_dict_values(json_dict: dict, method_name: str, *args) -> dict:
    """Convert json into appropriate format.

    :param json_dict:
    :param method_name:
    :param args:
    :return:
    """
    json_dictionary = {}

    for key in json_dict:
        key_list = list(args)
        key_list.append(key)
        if isinstance(json_dict[key], dict):
            json_dictionary[key] = convert_dict_values(json_dict[key], method_name, *key_list)
        else:
            json_dictionary[key] = convert_value(json_dict[key], method_name, *key_list)

    return json_dictionary


def convert_value(value: str, method_name: str, *keys):
    """Convert str value into specified type.

    :param value:
    :param keys:
    :param method_name:
    :return:
    """
    value_type = get_type_of_value(method_name, *keys)
    if value_type == CONST_INT:
        return int(value, 0)
    elif value_type == CONST_STRING:
        return value
    elif value_type == CONST_BOOL:
        return bool(value)
    elif value_type == CONST_ADDRESS:
        return Address(value[:2], bytes.fromhex(value[2:]))
    elif value_type == CONST_INT_ARRAY:
        tmp_str_array = _convert_into_str_array(value)
        return [int(a, 0) for a in tmp_str_array]
    elif value_type == CONST_BOOL_ARRAY:
        tmp_str_array = eval(value)
        return [string_to_bool(a) for a in tmp_str_array]
    elif value_type == CONST_STRING_ARRAY:
        return eval(value)
    elif value_type == CONST_ADDRESS_ARRAY:
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

    :param str_bool: ex) 'True', 'False'
    :return:
    """
    if bool(str_bool) is False or str_bool == "False":
        return False
    return True


def get_type_of_value(method_name: str, *keys) -> str:
    value_type = type_info[method_name]
    for key in keys:
        value_type = value_type[key]
    return value_type
