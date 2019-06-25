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

import typing

from ..base.type_converter import TypeConverter

if typing:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..base.block import Block


def get_main_preps(context: 'IconScoreContext'):
    preps: 'dict' = context.engine.prep.get_main_preps_in_term()
    if preps is None:
        preps = {}

    block: 'Block' = context.storage.icx.last_block
    preps['blockHeight'] = hex(0) if block is None else hex(block.height)
    block = context.storage.icx.last_block
    preps['blockHeight'] = 0 if block is None else block
    TypeConverter.convert_type_reverse(preps)
    result = {
        "result": preps
    }

    return result


inner_call_handler = {
    "ise_getPRepList": get_main_preps
}


def inner_call(context: 'IconScoreContext', request: dict):
    method = request['method']
    params = request.get("params", {})
    handler = inner_call_handler[method]
    return handler(context, **params)
