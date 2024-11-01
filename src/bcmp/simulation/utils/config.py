from enum import Enum
from typing import Any, Union
from pydantic import BaseModel, Field, root_validator

from bcmp.simulation.helpers.types import RequestType, ServerId, Route


class NetworkConfig(BaseModel):
    servers: list["ServerConfig"]
    generators: list["GeneratorConfig"]


class ServerType(Enum):
    FIFO = "fifo"
    IS = "is"
    PS = "ps"
    LIFO_PR = "lifo-pr"


class ServerConfig(BaseModel):
    id: ServerId
    type: ServerType
    params: dict[str, Any] = Field(default_factory=dict)

    process: Union["DistributionConfig",
                   dict[RequestType, "DistributionConfig"]]
    routes: Union["RoutingConfig", dict[RequestType, "RoutingConfig"]]

    @staticmethod
    def validate_and_wrap(values, key):
        item = values.get(key, {})
        matching_requests = [r.value in item for r in RequestType]
        assert all(matching_requests) or not any(matching_requests), \
            "Either all or none of request types must be defined"

        if item and not matching_requests[0]:
            values[key] = {req_type: item for req_type in RequestType}

    @root_validator(pre=True)
    def wrap_configs(cls, values):
        cls.validate_and_wrap(values, 'process')
        cls.validate_and_wrap(values, 'routes')
        return values


class GeneratorConfig(BaseModel):
    id: ServerId
    route: Route
    priority: int = 1
    generate: "DistributionConfig"


class DistributionType(Enum):
    POISSON = "poisson"
    EXPONENTIAL = "exponential"


class DistributionConfig(BaseModel):
    type: DistributionType
    params: dict[str, Any] = Field(default_factory=dict)


class RoutingType(Enum):
    RANDOM = "random"


class RoutingConfig(BaseModel):
    type: RoutingType
    routes: list["Route"]
