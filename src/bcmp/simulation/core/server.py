from typing import Protocol, TypedDict, Unpack, Callable, Any
from abc import ABC, abstractmethod
from datetime import timedelta
from functools import partial

from queue import Queue

from bcmp.simulation.core.timer import Timer, TimeDiff
from bcmp.simulation.helpers.types import Request, RequestType, Logger, ServerId, Route
from bcmp.simulation.utils.logger import log_request


type RouteRequestFn = callable[[RequestType], Route]
type GetProcessingTimeFn = callable[[RequestType], float]


class MessageBus:
    def __init__(self):
        self.receivers = {}

    def register_receiver(self, receiver: ServerId, callback: Callable[[Request], Any]) -> None:
        self.receivers[receiver] = callback

    def send(self, receiver: ServerId, request: Request) -> ...:
        if not receiver in self.receivers:
            raise Exception("Receiver not found")

        callback = self.receivers[receiver]
        return callback(request)


class Server(Protocol):
    """Protocol defining the interface for a server in the system."""

    @property
    def id(self) -> ServerId: ...

    @property
    def name(self) -> str: ...

    def receive(self, request: Request) -> bool: ...

    def tick(self) -> None: ...


class BaseServerInitArgs(TypedDict):
    id: ServerId
    logger: Logger
    timer: Timer
    message_bus: MessageBus
    route_request: RouteRequestFn
    get_processing_time: GetProcessingTimeFn


class BaseServer(ABC):
    def __init__(
        self,
        id: ServerId,
        logger: Logger,
        timer: Timer,
        message_bus: MessageBus,
        route_request: RouteRequestFn,
        get_processing_time: GetProcessingTimeFn
    ) -> None:
        super().__init__()
        self._id = id

        self._log = partial(log_request, logger.bind(source=self.name), timer)
        self._timer = timer
        self._message_bus = message_bus

        self._route_request = route_request

        self._get_processing_time = \
            lambda request_type: timer.round(get_processing_time(request_type))

        message_bus.register_receiver(id, self.receive)

    @ property
    def id(self) -> ServerId:
        return self._id

    @ property
    def name(self) -> str:
        return f"WS{self._id:>2}"

    def _send(self, request: Request) -> None:
        route = self._route_request(request.type)
        receiver, new_type = route.destination, route.request_type
        if not receiver:
            self._log(request, "🏁 Finished")
            return

        if new_type and new_type != request.type:
            self._log(request, "🔀 Swapped", f"({request.type.value}→{new_type.value})",
                      old_type=request.type.value, new_type=new_type.value)
            request.type = new_type

        self._message_bus.send(receiver, request)
        self._log(request, "⏩ Forwarded", f"({self.id}→{receiver})",
                  dest_id=receiver)

    @ abstractmethod
    def receive(self, request: Request) -> bool: ...

    @ abstractmethod
    def tick(self) -> None: ...


class ServerFIFO(BaseServer):
    def __init__(self, buffer_size: int, **kw: Unpack[BaseServerInitArgs]) -> None:
        super().__init__(**kw)
        self._queue: Queue[Request] = Queue(maxsize=buffer_size)

        self._wait_until, self._request = None, None

    def tick(self) -> None:
        if self._wait_until and self._wait_until > self._timer.time:
            return

        if request := self._request:
            self._send(request)
            self._log(request, "✅ Processed",
                      f"({request.metadata['processing_time']}s)")

        if self._queue.empty():
            self._request = self._wait_until = None
            return

        self._request = request = self._queue.get()
        processing_time = self._get_processing_time(request.type)
        self._wait_until = self._timer.time + processing_time

        processing_time = request.metadata['processing_time'] = f"{
            processing_time.total_seconds():.3f}"
        self._log(request, "🚀 Started", f"({processing_time}s to go)")

    def receive(self, request: Request) -> bool:
        if self._queue.full():
            self._log(request, "❌ Rejected", "(queue full)")
            return False

        self._queue.put(request)
        self._log(request, "⏳ Queued",
                  f"({self._queue.qsize()}/{self._queue.maxsize})")
        return True


class ServerPS(BaseServer):
    def __init__(self, **kw: Unpack[BaseServerInitArgs]) -> None:
        super().__init__(**kw)
        self._processing: dict[int, Request] = {}
        self._time_left: dict[int, TimeDiff] = {}

    def tick(self) -> None:
        if not self._processing:
            return

        time_slice = self._timer.resolution / len(self._processing)
        finished = []

        for request_id, request in self._processing.items():
            self._time_left[request_id] -= time_slice
            if self._time_left[request_id] <= timedelta(0):
                self._send(request)
                self._log(request, "✅ Processed",
                          f"({request.metadata['processing_time']}s)")
                finished.append(request_id)

        for request_id in finished:
            del self._processing[request_id]
            del self._time_left[request_id]

    def receive(self, request: Request) -> bool:
        processing_time = self._get_processing_time(request.type)

        self._processing[request.id] = request
        self._time_left[request.id] = processing_time

        processing_time = request.metadata['processing_time'] = f"{
            processing_time.total_seconds():.3f}"
        self._log(request, "🚀 Started", f"({processing_time}s to go)")

        return True


class ServerIS(BaseServer):
    def __init__(self, **kw: Unpack[BaseServerInitArgs]) -> None:
        super().__init__(**kw)
        self._processing = {}
        self._wait_until = {}

    def tick(self) -> None:
        current_time = self._timer.time
        finished = []

        for request_id, wait_until in self._wait_until.items():
            if wait_until <= current_time:
                request = self._processing[request_id]
                self._send(request)
                self._log(request, "✅ Processed",
                          f"({request.metadata['processing_time']}s)")
                finished.append(request_id)

        for request_id in finished:
            del self._processing[request_id]
            del self._wait_until[request_id]

    def receive(self, request: Request) -> bool:
        processing_time = self._get_processing_time(request.type)
        self._processing[request.id] = request
        self._wait_until[request.id] = self._timer.time + processing_time

        processing_time = request.metadata['processing_time'] = f"{
            processing_time.total_seconds():.3f}"
        self._log(request, "🚀 Started", f"({processing_time}s to go)")
        return True


class ServerLIFOPR(BaseServer):
    def __init__(self, **kw) -> None:
        super().__init__(**kw)
        self._requests: list[Request] = []
        self._time_left: dict[int, TimeDiff] = {}

        self._last_request = None
        self._in_progress = set()

    def tick(self) -> None:
        if not self._requests:
            self._last_request = None
            return

        request = self._requests[0]

        if self._last_request != request:
            msg = "🚀 Started" if request not in self._in_progress else "🔼 Resumed"
            self._in_progress.add(request)
            self._log(
                request, msg, f"({self._time_left[request.id].total_seconds():.3f}s to go)")
        self._last_request = request

        self._time_left[request.id] -= self._timer.resolution
        if self._time_left[request.id] <= timedelta(0):
            self._send(request)
            self._log(request, "✅ Processed",
                      f"({request.metadata['processing_time']}s)")
            del self._time_left[request.id]
            self._requests.pop(0)
            self._in_progress.remove(request)

    def receive(self, request: Request) -> bool:
        processing_time = self._get_processing_time(request.type)
        request.metadata['processing_time'] = f"{
            processing_time.total_seconds():.3f}"
        self._time_left[request.id] = processing_time

        insert_idx = next((i for i, r in enumerate(self._requests)
                           if r.priority < request.priority), len(self._requests))
        if self._requests:
            if insert_idx:
                self._log(request, "⏳ Queued",
                          f"({insert_idx}/{len(self._requests)})")
            else:
                self._log(self._requests[0], "⏸️  Interrupted",
                          f"({self._requests[0].priority}<{request.priority})")

        self._requests.insert(insert_idx, request)

        return True
