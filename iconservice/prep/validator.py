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

import re
from typing import TYPE_CHECKING

import iso3166

from ..base.exception import InvalidParamsException, InvalidRequestException
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import IISS_MIN_IREP, IISS_MAX_IREP_PERCENTAGE, IISS_MONTH, \
    PERCENTAGE_FOR_BETA_2, Revision

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from .data import PRep, Term
    from ..base.address import Address

scheme_pattern = r'^(http:\/\/|https:\/\/)'
path_pattern = r'(\/\S*)?$'
port_regex = r'(:[0-9]{1,5})?'
ip_regex = r'(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])'
host_name_regex = r'(localhost|(?:[\w\d](?:[\w\d-]{0,61}[\w\d])\.)+[\w\d][\w\d-]{0,61}[\w\d])'
email_regex = r'^[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*@' + host_name_regex + '$'
ENDPOINT_DOMAIN_NAME_PATTERN = re.compile(f'^{host_name_regex}{port_regex}$')
ENDPOINT_IP_PATTERN = re.compile(f'^{ip_regex}{port_regex}$')
WEBSITE_DOMAIN_NAME_PATTERN = re.compile(f'{scheme_pattern}{host_name_regex}{port_regex}{path_pattern}$')
WEBSITE_IP_PATTERN = re.compile(f'{scheme_pattern}{ip_regex}{port_regex}{path_pattern}$')
EMAIL_PATTERN = re.compile(email_regex)
EMAIL_LOCAL_PART_MAX = 64
EMAIL_MAX = 254


def validate_prep_data(context: 'IconScoreContext',
                       prep_address: 'Address',
                       tx_data: dict,
                       set_prep: bool = False):
    if not set_prep:
        fields_to_validate = (
            ConstantKeys.NAME,
            ConstantKeys.COUNTRY,
            ConstantKeys.CITY,
            ConstantKeys.EMAIL,
            ConstantKeys.WEBSITE,
            ConstantKeys.DETAILS,
            ConstantKeys.P2P_ENDPOINT,
        )

        for key in fields_to_validate:
            if key not in tx_data:
                raise InvalidParamsException(f'"{key}" not found')
            elif isinstance(tx_data[key], str) and len(tx_data[key].strip()) < 1:
                raise InvalidParamsException("Empty data not allowed")

    for key, value in tx_data.items():
        if value is None:
            continue
        if isinstance(value, str) and len(value.strip()) < 1:
            raise InvalidParamsException("Empty data not allowed")
        if key == ConstantKeys.P2P_ENDPOINT:
            _validate_p2p_endpoint(context, value)
        elif key in (ConstantKeys.WEBSITE, ConstantKeys.DETAILS):
            _validate_uri(value)
        elif key == ConstantKeys.EMAIL:
            _validate_email(context.revision, value)
        elif key == ConstantKeys.COUNTRY:
            _validate_country(value)

    # node address validate
    is_update_node_address: bool = \
        ConstantKeys.NODE_ADDRESS in tx_data and tx_data[ConstantKeys.NODE_ADDRESS] is not None
    if set_prep and not is_update_node_address:
        # non changed skip
        return

    # register_prep or is_update_node_address is True
    node_address: 'Address' = tx_data[ConstantKeys.NODE_ADDRESS] if is_update_node_address else prep_address
    context.prep_address_converter.validate_node_address(node_address)


def _validate_p2p_endpoint(context: "IconScoreContext", p2p_endpoint: str):
    network_locate_info = p2p_endpoint.split(":")

    if len(network_locate_info) != 2:
        raise InvalidParamsException("Invalid endpoint format. endpoint must have port info")

    _validate_port(network_locate_info[1], ConstantKeys.P2P_ENDPOINT)

    if not (ENDPOINT_IP_PATTERN.match(p2p_endpoint) or ENDPOINT_DOMAIN_NAME_PATTERN.match(p2p_endpoint.lower())):
        raise InvalidParamsException("Invalid endpoint format")

    if context.revision >= Revision.PREVENT_DUPLICATED_ENDPOINT.value:
        for active_prep in context.preps:
            if active_prep.p2p_endpoint == p2p_endpoint and context.tx.origin != active_prep.address:
                raise InvalidParamsException("Duplicated endpoint")


def _validate_uri(uri: str):
    uri = uri.lower()
    if WEBSITE_DOMAIN_NAME_PATTERN.match(uri):
        return
    if WEBSITE_IP_PATTERN.match(uri):
        return

    raise InvalidParamsException("Invalid uri format")


def _validate_port(port: str, validating_field: str):
    try:
        port = int(port, 10)
    except ValueError:
        raise InvalidParamsException(f'Invalid {validating_field} format. port: "{port}"')

    if not 0 < port < 65536:
        raise InvalidParamsException(f"Invalid {validating_field} format. Port out of range: {port}")


def _validate_email(revision: int, email: str):
    error_msg = "Invalid email format"
    if revision < Revision.FIX_EMAIL_VALIDATION.value:
        if not EMAIL_PATTERN.match(email):
            raise InvalidParamsException(error_msg)
    else:
        encoded_email = email.encode('utf-8')
        at_index = encoded_email.rfind(b'@')
        email_length = len(encoded_email)
        if not (1 <= at_index <= EMAIL_LOCAL_PART_MAX and at_index + 1 < email_length <= EMAIL_MAX):
            raise InvalidParamsException(error_msg)


def _validate_country(country_code: str):
    if country_code.upper() not in iso3166.countries_by_alpha3:
        raise InvalidParamsException("Invalid alpha-3 country code")


def validate_irep(context: 'IconScoreContext', irep: int, prep: 'PRep'):
    term: 'Term' = context.engine.prep.term
    _validate_irep(irep=irep,
                   prev_irep=prep.irep,
                   prev_irep_block_height=prep.irep_block_height,
                   term_start_block_height=term.start_block_height,
                   term_total_supply=term.total_supply,
                   main_prep_count=context.main_prep_count)


def validate_np_irep(context: 'IconScoreContext', irep: int):
    term: 'Term' = context.engine.prep.term
    _validate_irep(irep=irep,
                   prev_irep=term.irep,
                   prev_irep_block_height=0,
                   term_start_block_height=1,
                   term_total_supply=term.total_supply,
                   main_prep_count=context.main_prep_count)


def _validate_irep(irep: int,
                   prev_irep: int,
                   prev_irep_block_height: int,
                   term_start_block_height: int,
                   term_total_supply: int,
                   main_prep_count: int):

    """
    beta1 + beta2 <= total_supply * IISS_MAX_IREP_PERCENTAGE / 100
    = (1/2 * irep * MAIN_PREP_COUNT + 1/2 * irep * PERCENTAGE_FOR_BETA_2) * IISS_MONTH
    = irep * (MAIN_PREP_COUNT + PERCENTAGE_FOR_BETA_2) * IISS_MONTH / 2
    <= total_supply * IISS_MAX_IREP_PERCENTAGE / 100

    irep <= total_supply * IISS_MAX_IREP_PERCENTAGE / (IISS_MONTH / 2 * 100 * (MAIN_PREP_COUNT + PERCENTAGE_FOR_BETA_2)
    """

    if prev_irep_block_height >= term_start_block_height:
        raise InvalidRequestException("I-Rep can be changed only once during a term")

    min_irep: int = max(prev_irep * 8 // 10, IISS_MIN_IREP)  # 80% of previous irep

    maximum_calculated_irep: int = \
        term_total_supply * IISS_MAX_IREP_PERCENTAGE // \
        (IISS_MONTH // 2 * 100 * (main_prep_count + PERCENTAGE_FOR_BETA_2))

    max_irep: int = min(prev_irep * 12 // 10, maximum_calculated_irep)  # 120% of previous irep

    if not min_irep <= irep <= max_irep:
        raise InvalidParamsException(f"I-Rep({irep}) out of range: {min_irep:,} ~ {max_irep:,}")
