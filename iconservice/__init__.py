# Copyright 2017-2018 theloop Inc.
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
"""Package for objects which are related with Icon Services"""

from .base.address import Address
from .base.exception import *
from .icon_service_cli import main
from .iconscore.icon_container_db import VarDB, DictDB, ArrayDB
from .iconscore.icon_score_base import *
from .logger import Logger

# Version of iconservice.
__version__ = "0.9.3"


if __name__ == '__main__':
    main()
