import sys
import json
import nanoid
import random
import numpy as np
from enum import Enum
from types import MethodType
from typing import Protocol, Any, Iterator, Literal
from queue import Queue
from dataclasses import dataclass
from abc import abstractmethod, ABC
from loguru import logger
from loguru._logger import Logger

from pathlib import Path

from datetime import timedelta, datetime
from bcmp.simulation.config import ServerType, ServerId, RequestType, ServerConfig, DistributionConfig, RequestGeneratorConfig, RoutingConfig, DistributionType, FinishProcessing


LOGS_DIR = Path("logs")
DEFAULT_TIMER_PRECISION = 1e-3  # seconds


def log_format(record):
    level = record["level"].name.rjust(5)
    source = record["extra"].get("source", "????")
    time = record["extra"].get("ts") or f"{record['time']:mm:ss.SSS}"
    return f"{time} | {level} | [{source:>2}] {record['message']}\n"


def json_sink(path: str | Path):
    def log_saver(message):
        data = message.record.get("extra", {})
        with open(path, "a") as f:
            f.write(json.dumps(data) + "\n")
    return log_saver


logger.remove()
logger.add(sys.stderr, format=log_format, level="DEBUG")

type Time = datetime
type TimeDiff = timedelta

type GetReceiverFn = callable[RequestType,
                              tuple[ServerId | FinishProcessing, RequestType | None]]

type GetProcessingTimeFn = callable[RequestType, TimeDiff]


@dataclass(slots=True)
class Request:
    id: int
    type: RequestType
    priority: int = 1


class Messenger:
    def __init__(self):
        self.receivers = {}

    def register_receiver(self, receiver: ServerId, callback: GetReceiverFn) -> None:
        self.receivers[receiver] = callback

    def send(self, receiver: ServerId, request: Request) -> None:
        if not receiver in self.receivers:
            raise Exception("Receiver not found")

        callback = self.receivers[receiver]
        callback(request)


class Timer:
    def __init__(self, precision: float = DEFAULT_TIMER_PRECISION) -> None:
        self.precision = precision

        self.time: Time = datetime.min
        self.resolution: TimeDiff = timedelta(seconds=precision)

    def tick(self) -> None:
        self.time += self.resolution

    def ts(self) -> str:
        return self.time.strftime("%M:%S:%f")[:-3]

    def round(self, seconds: float) -> TimeDiff:
        return timedelta(seconds=round(seconds / self.precision) * self.precision)


class Server(ABC):
    def __init__(
        self,
        id: ServerId,
        logger: Logger,
        messenger: Messenger,
        timer: Timer,
        get_receiver: GetReceiverFn,
        get_processing_time: GetProcessingTimeFn
    ) -> None:
        super().__init__()

        self.id = id
        self.name = f"WS{self.id:>2}"
        self.logger = logger

        self.time = lambda: timer.time
        self.ts = lambda: timer.ts()
        self._send = messenger.send

        self.get_receiver = get_receiver
        self.get_processing_time = get_processing_time

        messenger.register_receiver(id, self.receive)

    def send(self, request: Request) -> None:
        receiver, new_type = self.get_receiver(request.type)
        if not receiver:
            self.log(request, "🏁 Finished")
            return

        if new_type and new_type != request.type:
            request.type = new_type
            self.log(request, "🔀 Swapped", f"({request.type.value}→{new_type.value})",
                     old_type=request.type.value, new_type=new_type.value)

        self._send(receiver, request)
        self.log(request, "⏩ Forwarded", f"({self.id}→{receiver})",
                 dest_id=receiver)

    def log(self, request: Request, message: str, message_extra: str = "",  **extra_kwargs):
        log_message = f"{message:<11} request {request.id:>3} {message_extra}".strip()  # noqa

        action = message.split(' ')[-1].lower()
        log_extra = dict(ts=self.ts(), source=f"WS{self.id:>2}",
                         action=action, request_id=request.id, **extra_kwargs)

        log_func = self.logger.info if action in [
            'finished', 'processed', 'rejected'] else self.logger.debug
        log_func(log_message, **log_extra)

    @abstractmethod
    def receive(self, request: Request) -> None: ...

    @abstractmethod
    def tick(self) -> None: ...


class Generator:
    pass


def distribution_poisson(lambda_: float) -> Iterator[float]:
    while True:
        yield np.random.exponential(1/lambda_)


def distribution_exponential(lambda_: float) -> Iterator[float]:
    while True:
        yield np.random.exponential(lambda_)


class ServerFIFO(Server):
    def __init__(self, buffer_size: int, **kw) -> None:
        super().__init__(**kw)
        self.queue: Queue[Request] = Queue(maxsize=buffer_size)

        self._wait_until, self._request = None, None

    def tick(self):
        if self._wait_until and self._wait_until > self.time():
            return

        if request := self._request:
            self.send(request)
            self.log(request, "✅ Processed",
                     f"({self._processing_time.total_seconds():.3f}s)")

        if self.queue.empty():
            self._request = self._wait_until = None
            return

        self._request = request = self.queue.get()
        self._processing_time = self.get_processing_time(request.type)
        self.log(request, "🚀 Started",
                 f"({self._processing_time.total_seconds():.3f}s to go)")

        self._wait_until = self.time() + self._processing_time

    def receive(self, request: Request):
        if self.queue.full():
            self.log(request, "❌ Rejected", "(queue full)")
            return

        self.queue.put(request)
        self.log(request, "⏳ Queued",
                 f"({self.queue.qsize()}/{self.queue.maxsize})")


def simulate():
    # this example network is shown in img/example.jpg, with the exception of different mu

    duration = 5  # seconds
    server_mu = 0.1  # seconds

    simulation_id = nanoid.generate(size=10)

    logger_sink = json_sink(LOGS_DIR / f"{simulation_id}.jsonl")
    handler_id = logger.add(logger_sink,
                            format="{message}", level="DEBUG")
    logger.info(f"Starting simulation {simulation_id}",
                starttime=datetime.now().isoformat(), id=simulation_id, duration=duration, server_mu=server_mu)

    timer = Timer()
    messenger = Messenger()
    time_generator = distribution_exponential(server_mu)

    server_kw = dict(
        logger=logger,
        timer=timer,
        messenger=messenger,
        get_processing_time=lambda _: timer.round(next(time_generator))
    )
    servers = [
        ServerFIFO(id=1, buffer_size=4,
                   get_receiver=lambda request_type:
                       (3, None) if request_type == RequestType.TYPE3
                       else random.choice([(2, RequestType.TYPE1), (2, RequestType.TYPE2)]),
                   **server_kw),
        ServerFIFO(id=2, buffer_size=4,
                   get_receiver=lambda _: (1, RequestType.TYPE2), **server_kw),
        ServerFIFO(id=3, buffer_size=4,
                   get_receiver=lambda _: (1, None), **server_kw),
    ]

    # for testing purposes insert a couple of requests into the first server
    for request in [
        Request(id=1, type=RequestType.TYPE1),
        Request(id=2, type=RequestType.TYPE2),
        Request(id=3, type=RequestType.TYPE3),
    ]:
        servers[0].queue.put(request)

    end_time = datetime.min + timedelta(seconds=duration)
    while timer.time <= end_time:
        for server in servers:
            server.tick()
        timer.tick()

    logger.remove(handler_id)


if __name__ == "__main__":
    simulate()
