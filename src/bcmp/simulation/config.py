from enum import Enum
import json
from pydantic import BaseModel, Field, root_validator
from typing import Literal, Any


type ServerId = int


class ServerType(Enum):
    FIFO = "fifo"
    IS = "is"
    PS = "ps"
    LIFO_PR = "lifo-pr"


class RequestType(Enum):
    TYPE1 = "type1"
    TYPE2 = "type2"
    TYPE3 = "type3"


class DistributionType(Enum):
    POISSON = "poisson"
    EXPONENTIAL = "exponential"


type FinishProcessing = None


class DistributionConfig(BaseModel):
    type: DistributionType
    params: dict[str, Any]


class RoutingConfig(BaseModel):
    request: RequestType | None = None
    probability: float = Field(..., ge=0, le=1)
    destination: ServerId | FinishProcessing


class ServerConfig(BaseModel):
    id: ServerId
    type: ServerType
    params: dict[str, Any]

    process: DistributionConfig | dict[RequestType, DistributionConfig]
    routes: list[RoutingConfig] | dict[RequestType, list[RoutingConfig]]

    @root_validator(pre=True)
    def wrap_configs(cls, values):
        process = values.get('process')
        if process and not isinstance(process, dict):
            values['process'] = {req_type: process for req_type in RequestType}

        routes = values.get('routes')
        if routes and not isinstance(routes, dict):
            values['routes'] = {req_type: routes for req_type in RequestType}

        return values


class RequestGeneratorConfig(BaseModel):
    generate: DistributionConfig
    route: RoutingConfig


class NetworkConfig(BaseModel):
    servers: list[ServerConfig]
    generators: list[RequestGeneratorConfig]


# def load_server_config() -> NetworkConfig:
#     with open("./configs/networks/n1.json", 'r') as f:
#         data = json.loads(f.read())
#     return NetworkConfig(**data)


# config = load_server_config()

# print(
#     config.servers[0].type
# )


# generator_config_example = RequestGeneratorConfig(
#     request=RequestType.TYPE1,
#     generate=DistributionConfig(
#         type="exponential",
#         params={"lambda_": 0.5}
#     ),
#     route=RoutingConfig(
#         probability=0.8,
#         destination=1
#     )
# )

# server_config_example = ServerConfig(
#     id=1,
#     type=ServerType.FIFO,
#     params={"capacity": 10},
#     process=DistributionConfig(
#         type="poisson",
#         params={"lambda_": 5}
#     ),
#     route=[
#         RoutingConfig(probability=0.6, destination=2),
#         RoutingConfig(probability=0.4, destination=None)
#     ]
# )
