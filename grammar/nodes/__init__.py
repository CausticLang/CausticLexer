#!/bin/python3

'''Implements grammar nodes'''

#> Imports
import re
import typing
import functools
from enum import Enum
from abc import ABC, abstractmethod, abstractproperty

from . import exceptions

from .. import __init__ as _root

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

__all__ = ['GrammarNode']

#> Header
# Base node
class GrammarNode(ABC):
    '''Base grammar node'''
    __slots__ = ('bound', 'name', 'args', 'return_mode')

    NOMATCH = object()

    @abstractproperty
    @classmethod
    def ReturnMode(cls) -> type[Enum]: pass

    bound: '_root.Grammar'
    name: str
    args: tuple[tuple, dict]
    return_mode: Enum

    failure: Exception | None = property(lambda _: None)

    def __init_subclass__(cls):
        if isinstance(__all__, tuple): return
        __all__.append(cls.__name__)
    def __init__(self, bind: '_root.Grammar', name: str, *args, return_mode: Enum | None = None, **kwargs):
        self.bound = bind
        self.name = name
        self.args = (args, kwargs)
        if self.ReturnMode is not None:
            if return_mode is None:
                self.return_mode = next(iter(self.ReturnMode))
            elif return_mode not in self.ReturnMode:
                raise TypeError(f'return_mode should be a {self.ReturnMode.__qualname__}: {return_mode!r}')
            else: self.return_mode = return_mode
        if callable(s := getattr(self, 'setup', None)): s(*args, **kwargs)

    def compile(self) -> None:
        '''(Re)compilation callback'''

    @abstractmethod
    def match(self, on: AbstractBufferMatcher) -> dict | None:
        '''Matches on the buffer-matcher `on`, if possible'''

    @functools.wraps(match, updated=())
    def __call__(self, *args, return_mode: Enum | None = None, **kwargs) -> typing.Any:
        '''
            Executes `.match()`, but also checks `.failure`
                and checks `return_mode`
        '''
        if (e := self.failure) is not None:
            raise exceptions.NodeNotReadyException(self.name, f'Node {self.name!r} is not ready') from e
        if self.ReturnMode is None:
            return self.match(*args, **kwargs)
        if return_mode is None: return_mode = self.return_mode
        elif return_mode not in self.ReturnMode:
            raise TypeError(f'return_mode should be a {self.ReturnMode.__qualname__}: {return_mode!r}')
        return self.match(*args, return_mode=return_mode, **kwargs)

# Nodes
class PatternNode(GrammarNode):
    '''
        References a pattern

        `return_mode` affects the return value of `.match()`:
          - `MATCH`: return the `re.Match` object, `<match>`
          - `DICT`: return a dict of the named capture groups, `<match>.groupdict()`
          - `SEQ`: return a tuple of the capture groups, `<match>.groups()`
          - `FULL`: return the entirety of the matching bytes, `<match>.group(0)`
    '''
    __slots__ = ('failure', 'pname', 'patt')

    ReturnMode = Enum('ReturnMode', ('MATCH', 'DICT', 'SEQ', 'FULL'))

    pname: str
    patt: re.Pattern | None
    return_mode: ReturnMode

    def setup(self, *, patt: str) -> None:
        self.failure = Exception('Node was never compiled')
        self.pname = patt
        self.patt = None

    def compile(self) -> None:
        if not self.bound.patterns.is_complete(self.pname):
            self.failure = ValueError(f'Required pattern {self.pname!r} is missing or incomplete')
            return
        self.patt = re.compile(self.bound.patterns[self.pname])
        self.failure = None

    def match(self, on: AbstractBufferMatcher, return_mode: ReturnMode) \
    -> object | re.Match | dict[str, bytes] | tuple[bytes, ...] | bytes:
        m = on(self.patt.match)
        if m is None: return self.NOMATCH # -> object
        match return_mode:
            case self.ReturnMode.MATCH: return m # -> re.Match
            case self.ReturnMode.DICT: return m.groupdict() # -> dict[str, bytes]
            case self.ReturnMode.SEQ: return m.groups() # -> tuple[bytes, ...]
            case self.ReturnMode.FULL: return m.group(0) # -> bytes


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
            if (m := node.match(on)) is not self.NOMATCH:
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
#</Header

#> Package >/
__all__.extend(exceptions.__all__)
from .exceptions import *
__all__ = tuple(__all__)
