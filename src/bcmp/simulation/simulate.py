import nanoid
from datetime import datetime, timedelta
from pathlib import Path


from bcmp.simulation.utils.logger import logger, json_sink
from bcmp.simulation.utils.load import create_network
from bcmp.simulation.utils.config import NetworkConfig

from bcmp.simulation.core.timer import Timer
from bcmp.simulation.core.server import MessageBus


def simulate(config_path: str | Path, duration: float = 5):
    simulation_id = nanoid.generate(size=10)

    logger_sink = json_sink(f"{simulation_id}.jsonl")
    handler_id = logger.add(logger_sink, format="{message}", level="DEBUG")

    logger.info(
        f"Starting simulation {simulation_id}",
        source="INIT",
        id=simulation_id,
        starttime=datetime.now().isoformat(),
        duration=duration,
        config_path=config_path,
    )

    with open(config_path, 'r') as f:
        config = NetworkConfig.parse_raw(f.read())

    timer = Timer()
    message_bus = MessageBus()

    servers, generators = create_network(config, message_bus, timer, logger)

    """ Uncommment when running example1
    from bcmp.simulation.helpers.types import Request, RequestType
    for request in [
        Request(id=1, type=RequestType.TYPE1),
        Request(id=2, type=RequestType.TYPE2),
        Request(id=3, type=RequestType.TYPE3),
    ]:
        servers[0]._queue.put(request)
    """

    entities = [*generators, *servers, timer]

    end_time = datetime.min + timedelta(seconds=duration)
    while timer.time <= end_time:
        for entity in entities:
            entity.tick()

    logger.remove(handler_id)

    return simulation_id


if __name__ == '__main__':
    # simulate("configs/networks/example1.json")
    # simulate("configs/networks/example2.json", duration=60)
    # simulate("configs/networks/network_good.json", duration=60)
    simulate("/Users/kacperjarzyna/Desktop/studia/kolejki/bcmp-networks/configs/networks/ex.json", duration=60)
