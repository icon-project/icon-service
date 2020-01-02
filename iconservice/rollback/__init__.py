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


__all__ = "get_backup_filename"

import os


def get_backup_filename(block_height: int) -> str:
    """

    :param block_height: the height of the block where we want to go back
    :return:
    """
    return f"{block_height:010d}.bak"


def check_backup_exists(backup_root_path: str, current_block_height: int, rollback_block_height: int) -> bool:
    """Check if backup files for rollback exist

    :param backup_root_path: the directory where backup files are located
    :param current_block_height: current state before rollback
    :param rollback_block_height: final state after rollback
    :return: True(exist) False(not exist)
    """
    if current_block_height < 1 or \
            rollback_block_height < 0 or \
            rollback_block_height > current_block_height:
        return False

    for block_height in range(current_block_height - 1, rollback_block_height - 1, -1):
        filename = get_backup_filename(block_height)
        path = os.path.join(backup_root_path, filename)
        if not os.path.isfile(path):
            return False

    return True
