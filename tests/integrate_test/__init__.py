#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import os
from shutil import rmtree
from time import time
from typing import Dict, Union

from iconservice.base.type_converter_templates import ConstantKeys

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


def get_score_path(score_root: str, package_name: str):
    return os.path.join(TEST_ROOT_PATH, 'integrate_test/samples', score_root, package_name)


def root_clear(score_path: str, state_db_path: str, iiss_db_path: str):
    rmtree(score_path, ignore_errors=True)
    rmtree(state_db_path, ignore_errors=True)
    rmtree(iiss_db_path, ignore_errors=True)


def create_timestamp():
    return int(time() * 10 ** 6)


def create_dummy_public_key(data: bytes) -> bytes:
    return b"\x04" + hashlib.sha3_512(data).digest()


def create_register_prep_params(index: int) -> Dict[str, Union[str, bytes]]:
    name = f"node{index}"

    return {
        ConstantKeys.NAME: name,
        ConstantKeys.EMAIL: f"node{index}@example.com",
        ConstantKeys.WEBSITE: f"https://node{index}.example.com",
        ConstantKeys.DETAILS: f"https://node{index}.example.com/details",
        ConstantKeys.P2P_END_POINT: f"https://node{index}.example.com:7100",
        ConstantKeys.PUBLIC_KEY: create_dummy_public_key(name.encode())
    }
