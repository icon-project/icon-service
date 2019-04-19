# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import TYPE_CHECKING, Optional

from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.exception import AccessDeniedException, MethodNotFoundException, InvalidParamsException
from ..icon_constant import GOVERNANCE_ADDRESS
from ..utils import to_camel_case

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext


def handle_system_call(context: 'IconScoreContext',
                       from_: 'Address',
                       value: int,
                       method: str,
                       args: Optional[tuple],
                       kwargs: Optional[dict]):
    """
    Handles system call.  Reject if the sender is a non-privileged account.

    :param context: IconScoreContext
    :param from_: msg sender
    :param value: ICX value of the call
    :param method: calling method
    :param args: positional arguments
    :param kwargs: keyword arguments
    """

    if str(from_) not in _AUTHORIZED_ACCOUNTS:
        raise AccessDeniedException("No permission")

    try:
        handler = _HANDLER[method]
        args = [] if args is None else args
        kwargs = {} if kwargs is None else kwargs
        return handler(context, value, *args, **kwargs)
    except KeyError:
        # Case of invoking handler functions with unknown method name
        raise MethodNotFoundException(f"Method not found: {method}")
    except TypeError:
        # Case of invoking handler functions with invalid parameter
        # e.g. 'missing required params' or 'unknown params'
        raise InvalidParamsException(f"Invalid parameters")


def _handle_get_score_deposit_info(context: 'IconScoreContext', value: int, address: 'Address'):
    """
    Handler for `getScoreDepositInfo`

    :param context: IconScoreContext
    :param value: unused value
    :param address: score address
    :return: score information in dict
            - Amount of available virtual STEPs
            - Deposit contracts in list
    """
    deposit_info = context.fee_engine.get_deposit_info(context, address, context.block.height)
    return None if deposit_info is None else deposit_info.to_dict(to_camel_case)


# System Address
SYSTEM_ADDRESS = ZERO_SCORE_ADDRESS

# Authorized accounts
_AUTHORIZED_ACCOUNTS = [GOVERNANCE_ADDRESS]

# handler for system call
# handler argument format should be `(context, icx_value, [args,...])`
_HANDLER = {
    'getScoreDepositInfo': _handle_get_score_deposit_info,
}
