import enum
import time

from iconservice.icon_constant import ConfigKey


def now():
    return int(time.time())


class Category(enum.Enum):
    FROM_ON_TX = 0


class DoSGuard:
    def __init__(self, conf: dict):
        self._statistics: dict = {c.value: {} for c in Category}
        self._ban_expired: dict = {c.value: {} for c in Category}

        self._last_reset_time: int = now()
        dos_guard: dict = conf[ConfigKey.DOS_GUARD]
        self._reset_time: int = dos_guard[ConfigKey.RESET_TIME]
        self._threshold: int = dos_guard[ConfigKey.THRESHOLD]
        self._ban_time: int = dos_guard[ConfigKey.BAN_TIME]

    def update(self, _from: str):
        if now() - self._last_reset_time >= self._reset_time:
            self._reset()
        self._add(category=Category.FROM_ON_TX, value=_from)

    def _reset(self):
        self._statistics = {c.value: {} for c in Category}
        self._last_reset_time: int = now()

    def _add(self, category: Category, value: str):
        self._validate(category=category, value=value)

        if value not in self._statistics[category.value]:
            self._statistics[category.value][value] = 1
        else:
            if self._statistics[category.value][value] >= self._threshold:
                self._ban_expired[category.value][value] = now() + self._ban_time
                raise Exception(f"Too many requests: {category.name}({value})")
            self._statistics[category.value][value] += 1

    def _validate(self, category: Category, value: str):
        if value in self._ban_expired[category.value]:
            if now() >= self._ban_expired[category.value][value]:
                del self._ban_expired[category.value][value]
            else:
                self._ban_expired[category.value][value] = now() + self._ban_time
                raise Exception(f"(Validate) Too many requests: {category.name}({value})")
