# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

from ..base.exception import ExceptionCode

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..icx.icx_engine import IcxEngine


class TransactionValidator(object):
    """Validate a transaction before putting it into txPool
    """
    def __init__(self, icx: 'IcxEngine') -> None:
        """Constructor

        :param icx: icx engine
        :param score_mapper:
        """
        self._icx = icx

    def validate(self, tx: dict, step_price: int) -> tuple:
        """Validate a transaction before acceptiong it
        If failed to validate a tx, client will get a json-rpc error response

        :param tx: dict including tx info
        :param step_price:
        :return: (code, message)
            success: (0, None), error: (code, 'error message')
        """
        ret = self._check_balance(tx, step_price)
        if not ret:
            return ExceptionCode.INVALID_REQUEST, 'Out of balance'

        ret = self._check_to_address(tx)
        if not ret:
            return ExceptionCode.INVALID_PARAMS, 'Score not found'

        code = ExceptionCode.OK
        return code, str(code)

    def _check_balance(self, tx: dict, step_price: int) -> bool:
        """Check the balance of from address is enough to pay for tx fee and value

        :param tx:
        :param step_price:
        :return: True(success), False(Failure)
        """
        _from = tx['from']
        value = tx.get('value', 0)
        step_limit = tx.get('step_limit', 0)
        balance = self._icx.get_balance(context=None, address=_from)

        return balance >= value + (step_limit * step_price)

    def _check_to_address(self, tx: dict) -> bool:
        """Check the validation of to

        :param tx:
        :return:
        """
        to = tx.get('to', None)
        if to and to.is_contract:
            return self._icx.storage.is_score_installed(
                context=None,
                icon_score_address=to)

        return True
