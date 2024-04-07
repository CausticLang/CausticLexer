#!/bin/python3

'''Nested nodes that can contain other nodes'''

#> Imports
import typing
import itertools
from enum import Enum
from collections import abc as cabc

from . import base

from . import GrammarMark

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('UnionNode', 'ListNode', 'RepeatNode')

class UnionNode(base.NodeWithReturnMode, base.MultiNestedNode):
    '''
        References multiple other nodes in a union, matching one of any of them

        `return_mode` affects the return value of `.match()`:
          - `PAIR`: returns both the name and value in a tuple, `('<name>', <match>)`
          - `STRUCT`: returns a dict, `{'name': '<name>', 'val': <match>}`
          - `NAME`: returns only the name, `'name'`
          - `VAL`: returns only the value, `match`
    '''
    __slots__ = ()

    ReturnMode = Enum('ReturnMode', ('PAIR', 'STRUCT', 'NAME', 'VAL'))
    return_mode: ReturnMode

    def match(self, on: AbstractBufferMatcher, *, return_mode: ReturnMode) \
    -> GrammarMark | tuple[str, typing.Any] | dict[typing.Literal['name', 'val'], typing.Any] | str | typing.Any:
        for name,node in self.nodes.items():
            if (m := node(on)) is not GrammarMark.NO_MATCH:
                break
        else: return GrammarMark.NO_MATCH # -> GrammarMark
        match self.return_mode:
            case self.ReturnMode.PAIR: return (name, m) # -> tuple[str, typing.Any]
            case self.ReturnMode.STRUCT: return {'name': name, 'val': m} # -> dict[typing.Literal['name', 'val'], typing.Any]
            case self.ReturnMode.NAME: return name # -> str
            case self.ReturnMode.VAL: return m # -> typing.Any

class ListNode(base.NodeWithReturnMode, base.MultiNestedNode):
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
    __slots__ = ('order',)

    BASE_COMPILE_ORDER_HINT = base.MultiNestedNode.BASE_COMPILE_ORDER_HINT + 50

    ReturnMode = Enum('ReturnMode', ('SEQ', 'DICT', 'UNPACK'))
    return_mode: ReturnMode

    order: tuple[str, ...]

    def setup(self, *, nodes: cabc.Sequence[str], **kwargs) -> None:
        super().setup(nodes=nodes, **kwargs)
        self.order = tuple(nodes)

    def match(self, on: AbstractBufferMatcher, *, return_mode: ReturnMode) \
    -> GrammarMark | tuple[typing.Any, ...] | dict[str, typing.Any] | (tuple[typing.Any, ...] | dict[str, typing.Any] | None | typing.Any):
        orig_pos = on.save_loc()
        matches = []
        for name in self.order:
            matches.append(self.nodes[name](on))
            if matches[-1] is GrammarMark.NO_MATCH:
                on.load_loc(orig_pas) # backtrack
                return GrammarMark.NO_MATCH # -> GrammarMark
        match return_mode:
            case self.ReturnMode.SEQ: return tuple(matches) # -> tuple[typing.Any, ...]
            case self.ReturnMode.DICT: return dict(zip(self.order, matches)) # -> dict[str, typing.Any]
            case self.ReturnMode.UNPACK: # -> (tuple[typing.Any, ...] | dict[str, typing.Any] | None)
                if not matches: return None # -> None
                if len(matches) == 1: return matches[0]
                if isinstance(matches[0], cabc.Mapping):
                    return dict.update(*(matches))
                return sum((m for m in matches[1:]), start=matches[0])

class RepeatNode(base.NodeWithReturnMode, base.SingleNestedNode):
    '''
        Matches a node multiple times, between `min` and `max`
        Note: backtracks if more than 1 and less than `min` nodes match

        If `max` is `None`, there is no upper bound

        `return_mode` affects the return value of `.match()`:
          - `SEQ`: return a tuple containing all matches
          - `FIRST`: returns the first match (note that subsequent matches are still made),
            returning `None` if there are no matches and `min` is `0`
          - `LAST`: returns the last match, returning `None` upon no matches if `min` is `0`
          - `COUNT`: returns the amount of matches
    '''
    __slots__ = ('min', 'max')

    BASE_COMPILE_ORDER_HINT = base.MultiNestedNode.BASE_COMPILE_ORDER_HINT - 50

    ReturnMode = Enum('ReturnMode', ('SEQ', 'FIRST', 'LAST', 'COUNT'))
    return_mode: ReturnMode

    min: int
    max: int | None

    def setup(self, *, min: int = 0, max: int | None = None, **kwargs) -> None:
        super().setup(**kwargs)
        self.min = min
        self.max = max
        if self.min < 0:
            raise ValueError(f'Invalid value for min: {self.min!r}, must not be negative')
        if self.max is not None:
            if self.max < 0:
                raise ValueError(f'Invalid value for max: {self.max!r}, must not be negative')
            if self.max <= self.min:
                raise ValueError(f'Invalid values for min/max: max of {self.max!r} is lower or equal to min of {self.min!r}')

    def match(self, on: AbstractBufferMatcher, *, return_mode: ReturnMode) \
    -> GrammarMark | tuple[typing.Any, ...] | (typing.Any | None) | (typing.Any | None) | int:
        save = on.save_loc()
        matches = []
        # get up to minimum
        if self.min:
            for _ in range(self.min):
                matches.append(self.node(on))
                if matches[-1] is GrammarMark.NO_MATCH:
                    on.load_loc(save) # backtrack
                    return GrammarMark.NO_MATCH # -> GrammarMark
        # get up to maximum
        for _ in (itertools.repeat(None) if self.max is None
                  else range(self.min, self.max)):
            m = self.node(on)
            if m is GrammarMark.NO_MATCH: break
            matches.append(m)
        # return
        match return_mode:
            case self.ReturnMode.SEQ: return tuple(matches) # -> tuple[typing.Any, ...]
            case self.ReturnMode.FIRST: return matches[0] if matches else None # -> (typing.Any | None)
            case self.ReturnMode.LAST: return matches[-1] if matches else None # -> (typing.Any | None)
            case self.ReturnMode.COUNT: return len(matches) # -> int
