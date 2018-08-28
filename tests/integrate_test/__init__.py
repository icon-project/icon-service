#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os

from time import time
from shutil import rmtree

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


def get_score_path(score_root: str, package_name: str):
    return os.path.join(TEST_ROOT_PATH, 'integrate_test/test_samples', score_root, package_name)


def root_clear(score_path: str, state_db_path: str):
    rmtree(score_path, ignore_errors=True)
    rmtree(state_db_path, ignore_errors=True)


def create_timestamp():
    return int(time() * 10 ** 6)
