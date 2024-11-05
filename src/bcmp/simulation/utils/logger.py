import sys
import json
from loguru import logger
from pathlib import Path

from bcmp.simulation.core.timer import Timer
from bcmp.simulation.helpers.types import Logger, Request


LOG_DIR = Path("logs")
LOG_LEVEL = "DEBUG"


def log_format(record):
    level = record["level"].name.rjust(5)
    source = record["extra"].get("source", "????")
    time = record["extra"].get("ts") or f"{record['time']:HH:mm:ss}"
    return f"{time} | {level} | [{source:>2}] {record['message']}\n"


def json_sink(path: str | Path):
    def log_saver(message):
        data = message.record.get("extra", {})
        with open(LOG_DIR / path, "a") as f:
            f.write(json.dumps(data) + "\n")
    return log_saver


logger.remove()
logger.add(sys.stderr, format=log_format, level=LOG_LEVEL)


def log_request(logger: Logger, timer: Timer, request: Request, message: str, message_extra: str = "",  **extra_kwargs):
    log_message = f"{message:<13} request {request.id:>3} {message_extra}".strip()

    action = message.split(' ')[-1].lower()
    log_extra = dict(ts=timer.ts, action=action,
                     request_id=request.id, type=request.type.value, **extra_kwargs)

    log_func = logger.info if action in [
        'finished', 'processed', 'rejected'] else logger.debug
    log_func(log_message, **log_extra)
