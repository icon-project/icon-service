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


from ..base.address import Address


class IconScoreBatch(dict):
    """Contains precommit states for an icon score
    """
    def __init__(self, address: Address) -> None:
        """Constructor

        :param address: icon_score_address
        """
        self.__address = address

    @property
    def address(self) -> Address:
        """icon_score_address
        """
        return self.__address
