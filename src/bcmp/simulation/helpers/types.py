import loguru._logger
from enum import Enum
from typing import Any
from dataclasses import dataclass, field


type ServerId = int
type Logger = loguru._logger.Logger


@dataclass(slots=True)
class Request:
    id: int
    type: "RequestType"
    priority: int = 1

    metadata: dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)


class RequestType(Enum):
    TYPE1 = "type1"
    TYPE2 = "type2"
    TYPE3 = "type3"


type FinishProcessing = None
type NoChange = None


@dataclass
class Route:
    destination: ServerId | FinishProcessing
    request_type: RequestType | NoChange = None
    probability: float = 1.0
