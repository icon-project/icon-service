# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

from typing import TYPE_CHECKING, List, Optional, Any

from .icon_score_step import StepType
from ..base.address import Address, ICON_ADDRESS_BYTES_SIZE, ICON_ADDRESS_BODY_SIZE
from ..base.exception import InvalidEventLogException
from ..icon_constant import DATA_BYTE_ORDER, Revision
from ..utils import int_to_bytes, byte_length_of_int

if TYPE_CHECKING:
    from .icon_score_constant import BaseType
    from .icon_score_context import IconScoreContext


class EventLog(object):
    """ A DataClass of a event log.
    """

    def __init__(
            self,
            score_address: 'Address',
            indexed: List['BaseType'],
            data: List['BaseType']) -> None:
        """
        Constructor

        :param score_address: an address of SCORE in which the event is invoked
        :param indexed: a list of indexed arguments including a event signature
        :param data: a list of normal arguments
        """

        assert score_address.is_contract
        assert isinstance(indexed, list)
        assert isinstance(data, list)

        self.score_address: 'Address' = score_address
        self.indexed: 'List[BaseType]' = indexed
        self.data: 'List[BaseType]' = data

    def __str__(self) -> str:
        return '\n'.join([f'{k}: {v}' for k, v in self.__dict__.items()])

    def to_dict(self, casing: Optional[callable] = None) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            if value is None:
                # Excludes properties which have `None` value
                continue

            new_dict[casing(key) if casing else key] = value

        return new_dict


class EventLogEmitter:
    @classmethod
    def emit_event_log(cls,
                       context: 'IconScoreContext',
                       score_address: 'Address',
                       event_signature: str,
                       arguments: List[Any],
                       indexed_args_count: int,
                       fee_charge: bool = False):
        """
        Puts a eventlog to the running context

        :param context: running context.
        :param score_address: score address which event is occurred at.
        :param event_signature: signature of the eventlog
        :param arguments: arguments of eventlog call
        :param indexed_args_count: count of the indexed arguments
        :param fee_charge: used for deciding whether fee will be charged for the event logs

        :return:
        """

        if context.readonly:
            raise InvalidEventLogException(
                'The event log can not be recorded on readonly context')

        if indexed_args_count > len(arguments):
            raise InvalidEventLogException(
                f'declared indexed_args_count is {indexed_args_count}, '
                f'but argument count is {len(arguments)}')

        event_size = EventLogEmitter.__get_byte_length(context, event_signature)
        indexed: List['BaseType'] = [event_signature]
        data: List['BaseType'] = []
        for i, argument in enumerate(arguments):
            event_size += EventLogEmitter.__get_byte_length(context, argument)

            # Separates indexed type and base type with keeping order.
            if i < indexed_args_count:
                indexed.append(argument)
            else:
                data.append(argument)

        # Counting steps only if fee_charge is True
        if fee_charge:
            context.step_counter.apply_step(StepType.EVENT_LOG, event_size)

        event = EventLog(score_address, indexed, data)
        context.event_logs.append(event)

    @classmethod
    def __get_byte_length(cls,
                          context: 'IconScoreContext',
                          data: 'BaseType') -> int:
        if data is None:
            return 0
        elif isinstance(data, int):
            return byte_length_of_int(data)
        elif isinstance(data, Address):
            if context.revision < Revision.THREE.value:
                return ICON_ADDRESS_BODY_SIZE
            else:
                return ICON_ADDRESS_BYTES_SIZE

        return len(cls.__get_bytes_from_base_type(data))

    @classmethod
    def __get_bytes_from_base_type(cls,
                                   data: 'BaseType') -> bytes:
        if isinstance(data, str):
            return data.encode('utf-8')
        elif isinstance(data, Address):
            return data.prefix.value.to_bytes(1, DATA_BYTE_ORDER) + data.body
        elif isinstance(data, bytes):
            return data
        elif isinstance(data, int):
            return int_to_bytes(data)
        else:
            raise InvalidEventLogException(f'Invalid data type: {type(data)}, data: {data}')

    @classmethod
    def get_ordered_bytes(cls,
                          index: int,
                          data: 'BaseType') -> bytes:
        bloom_data = index.to_bytes(1, DATA_BYTE_ORDER)
        if data is not None:
            bloom_data += cls.__get_bytes_from_base_type(data)
        return bloom_data
