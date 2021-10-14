import enum
import time

from iconcommons import Logger


def now():
    return int(time.monotonic())  # unit: second


class Category(enum.Enum):
    FROM_ON_TX = 0


class DoSGuard:
    def __init__(self, reset_time: int, threshold: int, ban_time: int):
        Logger.info(f"DoSGuard config: reset_time={reset_time}, threshold={threshold}, ban_time={ban_time}")
        self._statistics: dict = {c.value: {} for c in Category}
        self._ban_expired: dict = {c.value: {} for c in Category}

        self._reset_time: int = reset_time
        self._threshold: int = threshold
        self._ban_time: int = ban_time
        self._last_reset_time: int = now()

    def run(self, _from: str):
        cur_time: int = now()
        if cur_time - self._last_reset_time > self._reset_time:
            self._reset(cur_time)
        self._add(cur_time=cur_time, category=Category.FROM_ON_TX, value=_from)

    def _reset(self, cur_time: int):
        self._statistics = {c.value: {} for c in Category}
        self._last_reset_time: int = cur_time

    def _add(self, cur_time: int, category: Category, value: str):
        self._validate(cur_time=cur_time, category=category, value=value)

        category_statistics: dict = self._statistics[category.value]
        category_statistics[value] = category_statistics.get(value, 0) + 1
        if category_statistics[value] > self._threshold:
            self._ban_expired[category.value][value] = cur_time + self._ban_time
            raise Exception(f"Too many requests: {category.name}({value})")

    def _validate(self, cur_time: int, category: Category, value: str):
        if value in self._ban_expired[category.value]:
            if cur_time > self._ban_expired[category.value][value]:
                del self._ban_expired[category.value][value]
            else:
                self._ban_expired[category.value][value] = cur_time + self._ban_time
                raise Exception(f"(Validate) Too many requests: {category.name}({value})")
