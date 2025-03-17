from typing import Literal

from langgraph.types import Command, interrupt

from .node import Node, State


class NoPriceNode(Node):
    async def __call__(self, state: State) -> Command[Literal['START']]:
        response = interrupt({})
        state.update({'message': response.get('message', state['message'])})

        return Command(update=state, goto='START')
