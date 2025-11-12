from __future__ import annotations
import asyncio
from typing import Any, Awaitable, Callable, Dict, List


class Node:
    """
    Simple representation of a graph node.

    Each node:
    - has a unique name;
    - wraps a function that accepts and/or mutates state (dict or GraphState);
    - knows which nodes come next.

    This mirrors LangGraph’s Node interface conceptually but keeps
    zero external dependencies for now.
    """

    def __init__(
        self,
        name: str,
        func: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
        | Callable[[Dict[str, Any]], Dict[str, Any]],
    ):
        self.name = name
        self.func = func
        self.next: List["Node"] = []

    def connect(self, *nodes: "Node") -> "Node":
        """Connect this node to one or more downstream nodes."""
        self.next.extend(nodes)
        return self


class SimpleGraph:
    """
    Lightweight DAG executor that supports async + sync node functions.

    best-practice design:
    - deterministic ordering (BFS);
    - shallow merge of state between nodes;
    - no side effects outside provided state object.
    """

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.entrypoints: List[Node] = []

    def add_node(self, node: Node, entry: bool = False):
        """Register a node; mark as entrypoint if needed."""
        self.nodes[node.name] = node
        if entry:
            self.entrypoints.append(node)

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute nodes breadth-first and merge outputs into shared state."""
        frontier = list(self.entrypoints)
        seen = set()

        while frontier:
            node = frontier.pop(0)
            if node.name in seen:
                continue
            seen.add(node.name)

            # run node function (sync or async)
            result = node.func(state)
            if asyncio.iscoroutine(result):
                result = await result

            # merge returned data into shared state
            if isinstance(result, dict):
                state.update(result)

            # enqueue downstream nodes
            frontier.extend(node.next)

        return state