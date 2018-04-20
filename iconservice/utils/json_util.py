from ..base.address import Address

CONST_FOR_ADDRESS_CODE = 1
CONST_FOR_INT_CODE = 2
CONST_FOR_STR_CODE = 3


def convert_dict_values(json_dict):
    json_dictionary = {}

    for key in json_dict:
        if isinstance(json_dict[key], dict):
            json_dictionary[key] = convert_dict_values(json_dict[key])
        else:
            json_dictionary[key] = convert_value(json_dict[key])

    return json_dictionary


def check_type(str_value):
    if not isinstance(str_value, str):
        return CONST_FOR_STR_CODE
    prefix = str_value[:2]
    if len(str_value) == 42 and (prefix == "cx" or prefix == "hx"):
        return CONST_FOR_ADDRESS_CODE
    elif prefix == "0x":
        return CONST_FOR_INT_CODE
    else:
        return CONST_FOR_STR_CODE


def convert_value(str_value):
    if not isinstance(str_value, str):
        return str(str_value)
    if check_type(str_value) is CONST_FOR_ADDRESS_CODE:
        return Address(str_value[:2], bytes.fromhex(str_value[2:]))
    elif check_type(str_value) is CONST_FOR_INT_CODE:
        return int(str_value, 0)
    else:
        return str(str_value)
