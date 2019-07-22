# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import re
from typing import TYPE_CHECKING

from ..base.address import Address
from ..base.exception import InvalidParamsException, InvalidRequestException
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import IISS_MIN_IREP, IISS_ANNUAL_BLOCK, IISS_MAX_IREP_PERCENTAGE

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from .data import PRep
    from .term import Term

PORT_REGEX = r'(:[0-9]{1,5})?'
IP_REGEX = r'(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])'\
           + PORT_REGEX
HOST_NAME_REGEX = r'(localhost|(?:[\w\d](?:[\w\d-]{0,61}[\w\d])\.)+[\w\d][\w\d-]{0,61}[\w\d])' + PORT_REGEX
EMAIL_REGEX = r'^[a-zA-Z0-9-_.]+@[a-zA-Z0-9-_]+\.[a-zA-Z0-9-_]+\w$'


def validate_prep_data(tx_origin, data: dict, set_prep: bool = False):
    if not set_prep:
        fields_to_validate = (
            ConstantKeys.NAME,
            ConstantKeys.COUNTRY,
            ConstantKeys.CITY,
            ConstantKeys.EMAIL,
            ConstantKeys.WEBSITE,
            ConstantKeys.DETAILS,
            ConstantKeys.PUBLIC_KEY,
            ConstantKeys.P2P_ENDPOINT
        )

        for key in fields_to_validate:
            if key not in data:
                raise InvalidParamsException(f'"{key}" not found')
            elif len(data[key].strip()) < 1:
                raise InvalidParamsException("Can not set empty data")

    for key in data:
        if len(data[key].strip()) < 1:
            raise InvalidParamsException("Can not set empty data")
        if key == ConstantKeys.PUBLIC_KEY:
            _validate_prep_public_key(data[key], tx_origin)
        elif key == ConstantKeys.P2P_ENDPOINT:
            _validate_p2p_endpoint(data[key])
        elif key in (ConstantKeys.WEBSITE, ConstantKeys.DETAILS):
            _validate_uri(data[key])
        elif key == ConstantKeys.EMAIL:
            _validate_email(data[key])


def _validate_prep_public_key(public_key: bytes, address: 'Address'):
    public_key_hash_value = hashlib.sha3_256(public_key[1:]).digest()
    if address.body != public_key_hash_value[-20:]:
        raise InvalidParamsException("Invalid publicKey")


def _validate_p2p_endpoint(p2p_endpoint: str):

    network_locate_info = p2p_endpoint.split(":")

    if len(network_locate_info) != 2:
        raise InvalidParamsException("Invalid endpoint format. endpoint must have port info")

    _validate_port(network_locate_info[1], ConstantKeys.P2P_ENDPOINT)

    if re.match('^'+IP_REGEX+'$', p2p_endpoint):
        return

    if not re.match('^'+HOST_NAME_REGEX+'$', p2p_endpoint):
        raise InvalidParamsException("Invalid endpoint format")


def _validate_uri(uri: str):
    scheme_pattern = r'^(http:\/\/|https:\/\/)'
    path_pattern = r'(\/\S*)?$'
    uri_for_domain = scheme_pattern + HOST_NAME_REGEX + path_pattern
    uri_for_ip = scheme_pattern + IP_REGEX + path_pattern
    if re.match(uri_for_domain, uri):
        return
    if re.match(uri_for_ip, uri):
        return

    raise InvalidParamsException("Invalid uri format")


def _validate_port(port: str, validating_field: str):
    try:
        port = int(port, 10)
    except ValueError:
        raise InvalidParamsException(f'Invalid {validating_field} format. port: "{port}"')

    if not 0 < port < 65536:
        raise InvalidParamsException(f"Invalid {validating_field} format. Port out of range: {port}")


def _validate_email(email: str):
    if re.match(EMAIL_REGEX, email):
        return
    raise InvalidParamsException("Invalid email format")


def validate_irep(context: 'IconScoreContext', irep: int, prep: 'PRep'):
    prev_irep: int = prep.irep
    prev_irep_block_height: int = prep.irep_block_height
    term: 'Term' = context.engine.prep.term

    if prev_irep_block_height >= term.start_block_height:
        raise InvalidRequestException("Irep can be changed only once during a term")

    min_irep: int = max(prev_irep * 8 // 10, IISS_MIN_IREP)  # 80% of previous irep
    max_irep: int = prev_irep * 12 // 10  # 120% of previous irep

    if min_irep <= irep <= max_irep:
        beta: int = context.engine.issue.get_limit_inflation_beta(irep)
        # Prevent irep from causing to issue more than IISS_MAX_IREP% of total supply for a year
        if beta * IISS_ANNUAL_BLOCK > term.total_supply * IISS_MAX_IREP_PERCENTAGE // 100:
            raise InvalidParamsException(f"Irep out of range: beta{beta} * ANNUAL_BLOCK > "
                                         f"prev_term_total_supply{term.total_supply} * "
                                         f"{IISS_MAX_IREP_PERCENTAGE} // 100")
    else:
        raise InvalidParamsException(f"Irep out of range: {irep}, {prev_irep}")
