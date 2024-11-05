from typing import Iterator

from bcmp.simulation.utils.config import *
import bcmp.simulation.helpers.distributions as distribution
import bcmp.simulation.helpers.routing as routing

from bcmp.simulation.core.timer import Timer
from bcmp.simulation.core.server import MessageBus, Server, ServerFIFO, ServerIS, ServerPS, ServerLIFOPR
from bcmp.simulation.core.generator import Generator

from bcmp.simulation.helpers.types import Logger


def create_network(config: NetworkConfig, message_bus: MessageBus, timer: Timer, logger: Logger) -> tuple[list[Server], list[Generator]]:
    entities = dict(message_bus=message_bus, timer=timer, logger=logger)

    servers = [create_server(server_config, **entities)
               for server_config in config.servers]
    generators = [create_generator(generator_config, **entities)
                  for generator_config in config.generators]

    return servers, generators


def create_server(config: ServerConfig, message_bus: MessageBus, timer: Timer, logger: Logger) -> Server:
    get_processing_time = {req_type: create_distribution(config.process[req_type])
                           for req_type in RequestType}
    route_request = {req_type: create_routing(config.routes[req_type])
                     for req_type in RequestType}

    server_args = config.params | dict(
        id=config.id,
        logger=logger,
        timer=timer,
        message_bus=message_bus,
        route_request=lambda request_type: route_request[request_type.value](),
        get_processing_time=lambda request_type: next(get_processing_time[request_type])
    )

    match config.type:
        case ServerType.FIFO:
            return ServerFIFO(**server_args)
        case ServerType.IS:
            return ServerIS(**server_args)
        case ServerType.PS:
            return ServerPS(**server_args)
        case ServerType.LIFO_PR:
            return ServerLIFOPR(**server_args)

    raise ValueError(f"Unknown server type: {config.type}")


def create_generator(config: GeneratorConfig, message_bus: MessageBus, timer: Timer, logger: Logger) -> Generator:
    return Generator(
        id=config.id,
        route=config.route,
        priority=config.priority,
        logger=logger,
        timer=timer,
        send=message_bus.send,
        get_sleep_time=create_distribution(config.generate)
    )


def create_distribution(config: DistributionConfig) -> Iterator[float]:
    match (config.type):
        case DistributionType.POISSON:
            return distribution.poisson(**config.params)
        case DistributionType.EXPONENTIAL:
            return distribution.exponential(**config.params)

    raise ValueError(f"Unknown distribution: {config.type}")


def create_routing(config: RoutingConfig) -> routing.RoutingFn:
    match (config.type):
        case RoutingType.RANDOM:
            return lambda: routing.random_weighted(config.routes)

    raise ValueError(f"Unknown routing: {config.type}")
