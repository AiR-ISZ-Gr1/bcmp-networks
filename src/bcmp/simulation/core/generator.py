from functools import partial
from typing import Iterator

from bcmp.simulation.core.timer import Timer
from bcmp.simulation.helpers.types import Logger, ServerId, Request, Route
from bcmp.simulation.utils.logger import log_request


type SendFn = callable[[ServerId, Request], ...]


class Generator:
    @staticmethod
    def _id_generator():
        id = 0
        while True:
            yield id
            id += 1

    _request_id = _id_generator()

    def __init__(
        self,
        id: int,
        route: Route,
        priority: int,
        logger: Logger,
        timer: Timer,
        send: SendFn,
        get_sleep_time: Iterator[float],
    ) -> None:
        self._id = id
        self._route = route
        self._priority = priority

        self._log = partial(log_request, logger.bind(source=self.name), timer)
        self._timer = timer
        self._send = send

        self._get_sleep_time = get_sleep_time

        self._wait_until = None

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return f"GN{self._id:>2}"

    def tick(self) -> None:
        if self._wait_until is None:
            self._wait_until = self._timer.time + \
                self._timer.round(next(self._get_sleep_time))
            return

        if self._timer.time <= self._wait_until:
            return

        request = Request(
            id=next(self._request_id),
            type=self._route.request_type,
            priority=1,
        )

        self._send(self._route.destination, request)
        self._log(request, "🆕 Generated", f"(→{self._route.destination})")

        self._wait_until = self._timer.time + \
            self._timer.round(next(self._get_sleep_time))
