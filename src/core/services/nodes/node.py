from abc import ABC, abstractmethod, abstractproperty
from typing import TypedDict


class State(TypedDict):
    message: str
    client_cpm: str
    influencer_price: str
    min_views: str
    max_views: str


class Node(ABC):
    engine = None

    @staticmethod
    def _calc_cap(state):
        return str(
            int(int(state.get('client_cpm')) / 4000 * (int(state.get('min_views')) + 3 * int(state.get('max_views')))))

    @staticmethod
    def condition_start_price(state):
        client_cpm = int(state.get("client_cpm", 0))
        min_views = int(state.get("min_views", 0))
        influencer_price = int(state.get("influencer_price", 0))

        return influencer_price <= (client_cpm * min_views) / 1000

    @abstractmethod
    async def __call__(self, state: State):
        pass

    def __init__(self, engine):
        self.engine = engine
