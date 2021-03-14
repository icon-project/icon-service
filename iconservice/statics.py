import enum
import time

from iconservice.icon_constant import ConfigKey


def now():
    return int(time.time())


class Category(enum.Enum):
    IP = 0
    FROM_ON_TX = 1


class Statics:
    def __init__(self, conf: dict):
        self._statics: dict = {c.value: {} for c in Category}
        self._ban: dict = {c.value: {} for c in Category}

        self._last_reset_time: int = now()
        self._diff_reset_time: int = conf[ConfigKey.DIFF_RESET_TIME]
        self._dos_check_count: int = conf[ConfigKey.DOS_CHECK_COUNT]
        self._release_time: int = conf[ConfigKey.DOS_RELEASE_TIME]

    def update(self, ip: str, params: dict):
        if now() - self._last_reset_time >= self._diff_reset_time:
            self._reset()
            self._update(ip, params)
        else:
            self._update(ip, params)

    def _reset(self):
        self._statics = {c.value: {} for c in Category}
        self._last_reset_time: int = now()

    def _update(self, ip: str, params: dict):
        # self._add(category=Category.IP, value=ip)

        method: str = params.get("method", "")
        if method == "icx_sendTransaction":
            self._add(category=Category.FROM_ON_TX, value=params["params"]["from"])
        else:
            pass

    def _add(self, category: Category, value: str):
        self._validate(category=category, value=value)

        if value not in self._statics[category.value]:
            self._statics[category.value][value] = 1
        else:
            if self._statics[category.value][value] >= self._dos_check_count:
                self._ban[category.value][value] = now() + self._release_time
                raise Exception(f"Too much call: {category.name}({value})")
            self._statics[category.value][value] += 1

    def _validate(self, category: Category, value: str):
        if value in self._ban[category.value]:
            if now() >= self._ban[category.value][value]:
                del self._ban[category.value][value]
            else:
                self._ban[category.value][value] = now() + self._release_time
                raise Exception(f"(validate) Too much call: {category.name}({value})")
