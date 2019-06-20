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
from typing import TYPE_CHECKING

from ..iconscore.icon_score_context import IconScoreContext

if TYPE_CHECKING:
    from ..base.block import Block
    from ..prep.data.prep_container import PRepContainer


def get_preps_root_hash(prep_ids_in_bytes: bytes) -> bytes:
    return hashlib.sha3_256(prep_ids_in_bytes).digest()


def get_preps(context: IconScoreContext):
    preps: 'PRepContainer' = context.engine.prep.term.main_preps
    prep_result = []
    prep_ids_in_bytes = b''

    for prep in preps:
        data = {
            "id": str(prep.address),
            "publicKey": f"0x{bytes.hex(prep.public_key)}",
            "p2pEndPoint": prep.p2p_end_point
        }
        prep_result.append(data)
        prep_ids_in_bytes = prep_ids_in_bytes + prep.address.to_bytes()

    block: 'Block' = context.storage.icx.last_block
    result = {
        "result": {
            "blockHeight": 0 if block is None else block.height,
            "preps": prep_result,
            "rootHash": ""
        }
    }
    if prep_result:
        root_hash = get_preps_root_hash(prep_ids_in_bytes)
        result['rootHash'] = f"0x{root_hash.hex()}"

    return result


inner_call_handler = {
    "ise_getPRepList": get_preps
}


def inner_call(context: IconScoreContext, request: dict):
    method = request['method']
    params = request.get("params", {})
    handler = inner_call_handler[method]
    return handler(context, **params)
