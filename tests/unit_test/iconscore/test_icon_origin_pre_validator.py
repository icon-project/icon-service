import pytest
import os
import random

from iconservice.iconscore.icon_pre_validator import IconPreValidator
from iconservice.base.address import (
    Address,
    AddressPrefix
)
from iconservice.base.exception import (
    InvalidRequestException,
    InvalidParamsException
)


def make_required_parameters(**kwargs) -> dict:
    return {
        'version': kwargs['version'],
        'from': kwargs['_from'],
        'to': kwargs['to'],
        'stepLimit': kwargs['stepLimit'],
        'nid': '0x1',
        'timestamp': kwargs['timestamp'],
        'signature': kwargs['signature'],
    }


def make_origin_parameters(option: dict = None) -> dict:
    params = make_required_parameters(
        version=hex(3),
        _from=str(Address.from_data(AddressPrefix.EOA, os.urandom(20))),
        to=str(Address.from_data(random.choice([AddressPrefix.EOA, AddressPrefix.CONTRACT]), os.urandom(20))),
        stepLimit=hex(random.randint(10, 5000)),
        timestamp=hex(random.randint(10, 5000)),
        signature='VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA='
    )

    if option:
        params.update(option)
    return params


@pytest.fixture
def validator():
    validator = IconPreValidator()
    return validator


@pytest.mark.parametrize(
    'malformed_value, expected',
    [
        ('', False),
        ('0x0001', False),
        ('0x0000001', False),
        ('100', False),
        ('0x1e', True)
    ]
)
def test_malformed_number_string(validator, malformed_value, expected):
    assert validator.is_integer_type(malformed_value) == expected


@pytest.mark.parametrize(
    'malformed_value, expected',
    [
        ('', False),
        ('0x1A', False),
        ('0x3E', False),
        ('0xBE', False),
        ('0Xff', False),
        ('0xff', True)
    ]
)
def test_malformed_uppercase_string(validator, malformed_value, expected):
    assert validator.is_integer_type(malformed_value) == expected


@pytest.mark.parametrize(
    'malformed_value, expected',
    [
        ('', False),
        ('0xqw1234', False),
        ('hxEfe3', False),
        ('hx1234', False),
        ('cx1234', False),
        ('cxEab1', False),
        ('1234', False),
        ('hx3f945d146a87552487ad70a050eebfa2564e8e5c', True)
    ]
)
def test_malformed_address(validator, malformed_value, expected):
    assert validator.is_address_type(malformed_value) == expected


@pytest.mark.parametrize(
    'msg',
    [
        {},
        make_origin_parameters({'version': '0x1'}),
        make_origin_parameters({'version': '0x2'}),
    ]
)
def test_pre_validate_version(validator, msg):
    with pytest.raises(InvalidRequestException):
        validator.origin_pre_validate_version(msg)


@pytest.mark.parametrize(
    'msg',
    [
        {},
        {'version': '0x3'},
        {'version': '0x3', 'from': 'temp', 'to': 'temp', 'stepLimit': 'temp', 'timestamp': 'test'},
        make_origin_parameters({
            'value': '',
            'nonce': '',
            'data_type': '',
            'data': '',
            'item': '',
            'test': '',
            'failed': '',
            'failure': ''
        })
    ]
)
def test_pre_validate_params(validator, msg):
    with pytest.raises(InvalidRequestException):
        validator.origin_pre_validate_params(msg)


@pytest.mark.parametrize(
    'param',
    [
        '',
        None,
        'foo',
        'bar'
    ]
)
def test_validate_param(validator, param):
    with pytest.raises(InvalidParamsException):
        validator.origin_validate_param(param)


@pytest.mark.parametrize(
    'param, value',
    [
        ('stepLimit', ''),
        ('stepLimit', 'Fx35'),
        ('to', '0xFF'),
        ('value', '0X1e'),
        ('to', 'cX3F9e')
    ]
)
def test_validate_value(validator, param, value):
    with pytest.raises(InvalidRequestException):
        validator.origin_validate_value(param, value)


@pytest.mark.parametrize(
    'msg',
    [
        make_origin_parameters({'test': 'foo'}),
        make_origin_parameters({'to': 'hxEE'}),
        make_origin_parameters({'stepLimit': '0xEf'}),
    ]
)
def test_validate_fields(validator, msg):
    with pytest.raises((InvalidRequestException, InvalidParamsException)):
        validator.origin_validate_fields(msg)


@pytest.mark.parametrize(
    'msg',
    [
        {},
        make_origin_parameters({'version': '0x1'}),
        make_origin_parameters({'to': 'hxFF'}),
        make_origin_parameters({'value': '0x001'})
    ]
)
def test_validate_request_execute(validator, msg):
    with pytest.raises((InvalidParamsException, InvalidRequestException)):
        validator.origin_request_execute(msg)

