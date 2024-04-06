#!/bin/python3

'''Nested nodes that can contain other nodes'''

#> Imports
import typing
import itertools
from enum import Enum

from . import GrammarNode

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('UnionNode', 'ListNode', 'RepeatNode')

class UnionNode(GrammarNode):
    '''
        References multiple other nodes in a union, matching one of any of them

        `return_mode` affects the return value of `.match()`:
          - `PAIR`: returns both the name and value in a tuple, `('<name>', <match>)`
          - `STRUCT`: returns a dict, `{'name': '<name>', 'val': <match>}`
          - `NAME`: returns only the name, `'name'`
          - `VAL`: returns only the value, `match`
    '''
    __slots__ = ('failure', 'nodes')

    ReturnMode = Enum('ReturnMode', ('PAIR', 'STRUCT', 'NAME', 'VAL'))

    nodes: dict[str, GrammarNode | None]
    return_mode: ReturnMode

    def setup(self, *nodes: str) -> None:
        self.failure = Exception('Node was never compiled')
        self.nodes = dict.fromkeys(nodes, None)

    def compile(self) -> None:
        for node in self.nodes.keys():
            if node not in self.bound.nodes:
                self.failure = KeyError(f'Required node {node!r} is missing')
                return
            n = self.nodes[node] = self.bound.nodes[node]
            if n.failure is not None:
                self.failure = ValueError(f'Required node {node!r} failed to compile')
                self.failure.__context__ = n.failure
                return
        self.failure = None

    def match(self, on: AbstractBufferMatcher, *, return_mode: ReturnMode) \
    -> object | tuple[str, typing.Any] | dict[typing.Literal['name', 'val'], typing.Any] | str | typing.Any:
        for name,node in self.nodes.items():
            if (m := node(on)) is not self.NOMATCH:
                break
        else: return self.NOMATCH # -> object
        match self.return_mode:
            case self.ReturnMode.PAIR: return (name, m) # -> tuple[str, typing.Any]
            case self.ReturnMode.STRUCT: return {'name': name, 'val': m} # -> dict[typing.Literal['name', 'val'], typing.Any]
            case self.ReturnMode.NAME: return name # -> str
            case self.ReturnMode.VAL: return m # -> typing.Any

class ListNode(GrammarNode):
    '''
        References multiple other nodes in order,
            only matching when all of them match
        Note: backtracks if any node after the first doesn't match

        `return_mode` affects the return value of `.match()`:
          - `SEQ`: returns the nodes in a tuple, `(<match0>, <match1>, <match2>)`
          - `DICT`: returns the nodes with their names, `{<node0>.name: <match0>, <node1>.name: <match1>, <node2>.name: <match2>}`
            Note: if a named node is used more than once, the last match of that node will be used
                Otherwise, order is preserved as well
          - `UNPACK`: unpacks the contents of the nodes into a tuple or dict
            Note: this will fail if not all nodes share a return type compatible with tuple (`*`, `Sequence`) or dict (`**`, `Mapping`)
            Note: this will return `None` if there are no nodes, and the value of the only node if there is only one node
    '''
    __slots__ = ('failure', 'nodes', 'order')

    ReturnMode = Enum('ReturnMode', ('SEQ', 'DICT', 'UNPACK'))

    nodes: dict[str, GrammarNode | None]
    order: tuple[str, ...]
    return_mode: ReturnMode

    def setup(self, *nodes: str) -> None:
        self.failure = Exception('Node was never compiled')
        self.order = nodes
        self.nodes = dict.fromkeys(nodes, None)

    def compile(self) -> None:
        for node in self.order:
            if node not in self.bound.nodes:
                self.failure = KeyError(f'Required node {node!r} is missing')
                return
            n = self.nodes[node] = self.bound.nodes[node]
            if n.failure is not None:
                self.failure = ValueError(f'Required node {node!r} failed to compile')
                self.failure.__context__ = n.failure
                return
        self.failure = None

    def match(self, on: AbstractBufferMatcher, *, return_mode: ReturnMode) \
    -> object | tuple[typing.Any, ...] | dict[str, typing.Any] | (tuple[typing.Any, ...] | dict[str, typing.Any] | None | typing.Any):
        orig_pos = on.save_loc()
        matches = []
        for name in self.order:
            matches.append(self.nodes[name](on))
            if matches[-1] is self.NOMATCH:
                on.load_loc(orig_pas) # backtrack
                return self.NOMATCH # -> object
        match return_mode:
            case self.ReturnMode.SEQ: return tuple(matches) # -> tuple[typing.Any, ...]
            case self.ReturnMode.DICT: return dict(zip(self.order, matches)) # -> dict[str, typing.Any]
            case self.ReturnMode.UNPACK: # -> (tuple[typing.Any, ...] | dict[str, typing.Any] | None)
                if not matches: return None # -> None
                if len(matches) == 1: return matches[0]
                if isinstance(matches[0], cabc.Mapping):
                    return dict.update(*(matches))
                return sum((m for m in matches[1:]), start=matches[0])

class RepeatNode(GrammarNode):
    '''
        Matches a pattern multiple times, between `min` and `max`
        Note: backtracks if more than 1 and less than `min` nodes match

        If `max` is `None`, there is no upper bound

        `return_mode` affects the return value of `.match()`:
          - `SEQ`: return a tuple containing all matches
          - `FIRST`: returns the first match (note that subsequent matches are still made),
            returning `None` if there are no matches and `min` is `0`
          - `LAST`: returns the last match, returning `None` upon no matches if `min` is `0`
          - `COUNT`: returns the amount of matches
    '''
    __slots__ = ('failure', 'node_name', 'node', 'min', 'max')

    ReturnMode = Enum('ReturnMode', ('SEQ', 'FIRST', 'LAST', 'COUNT'))

    node_name: str | None
    node: GrammarNode | None
    min: int
    max: int | None

    def setup(self, node: str, *, min: int = 0, max: int | None = None) -> None:
        self.failure = Exception('Node was never compiled')
        self.node_name = node
        self.node = None
        self.min = min
        self.max = max
        if (self.max is not None) and (self.min >= self.max):
            raise ValueError(f'min {self.min!r} cannot be higher than or equal to max {self.max!r}')

    def compile(self) -> None:
        if self.node_name is None: return
        if self.node_name not in self.bound.nodes:
            self.failure = KeyError(f'Required node {self.node_name!r} is missing')
            return
        self.node = self.bound.nodes[self.node_name]
        if self.node.failure is not None:
            self.failure = ValueError(f'Required node {self.node_name!r} failed to compile')
            self.failure.__context__ = self.node.failure
        self.failure = None

    def match(self, on: AbstractBufferMatcher, *, return_mode: ReturnMode) \
    -> object | tuple[typing.Any, ...] | (typing.Any | None) | (typing.Any | None) | int:
        save = on.save_loc()
        matches = []
        # get up to minimum
        if self.min:
            for _ in range(self.min):
                matches.append(self.node(on))
                if matches[-1] is self.NOMATCH:
                    on.load_loc(save) # backtrack
                    return self.NOMATCH # -> object
        # get up to maximum
        for _ in (itertools.repeat(None) if self.max is None
                  else range(self.min, self.max)):
            m = self.node(on)
            if m is self.NOMATCH: break
        # return
        match return_mode:
            case self.ReturnMode.SEQ: return tuple(matches) # -> tuple[typing.Any, ...]
            case self.ReturnMode.FIRST: return matches[0] if matches else None # -> (typing.Any | None)
            case self.ReturnMode.LAST: return matches[-1] if matches else None # -> (typing.Any | None)
            case self.ReturnMode.COUNT: return len(matches) # -> int
