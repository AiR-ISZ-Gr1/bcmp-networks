import random
from bcmp.simulation.helpers.types import Route

type RoutingFn = callable[[list[Route], ...], Route]


def random_weighted(routes: list[Route]):
    route = random.choices(
        routes,
        weights=[route.probability for route in routes]
    )[0]
    return route
