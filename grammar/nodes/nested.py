#!/bin/python3

'''Nested nodes that can contain other nodes'''

#> Imports
import typing
from enum import Enum

from . import GrammarNode

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('UnionNode', 'ListNode')

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
        success = False
        for name in self.order:
            matches.append(self.nodes[name](on))
        else: success = bool(self.order)
        if not success:
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
