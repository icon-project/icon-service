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

from typing import TYPE_CHECKING

from iconcommons import Logger

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


def get_step_trace_msg(context: "IconScoreContext"):
    tx_hash = context.tx.hash
    if isinstance(tx_hash, bytes):
        tx_hash = f"0x{tx_hash.hex()}"
    elif isinstance(tx_hash, str):
        tx_hash = f"0x{tx_hash}"
    step_trace_msg = f"transaction {tx_hash} consumed step following order : " \
                     f"{context.step_counter.step_tracer}" \
        if context.step_counter.step_tracer is not None else None
    return step_trace_msg


def print_step_trace(step_trace_msg: str, log_level: str):
    logging_function = getattr(Logger, log_level)
    logging_function(step_trace_msg, "STEPORDER")
