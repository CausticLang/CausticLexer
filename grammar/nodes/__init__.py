#!/bin/python3

'''Implements grammar nodes'''

#> Imports
import re
import typing
import functools
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
    __slots__ = ('bound', 'name', 'args')

    bound: '_root.Grammar'
    name: str
    args: tuple[tuple, dict]

    failure: Exception | None = property(lambda _: None)

    def __init_subclass__(cls):
        if isinstance(__all__, tuple): return
        __all__.append(cls.__name__)
    def __init__(self, bind: '_root.Grammar', name: str, *args, **kwargs):
        self.bound = bind
        self.name = name
        self.args = (args, kwargs)
        if callable(s := getattr(self, 'setup', None)): s(*args, **kwargs)

    def compile(self) -> None:
        '''(Re)compilation callback'''

    @abstractmethod
    def match(self, on: AbstractBufferMatcher) -> dict | None:
        '''Matches on the buffer-matcher `on`, if possible'''

    @functools.wraps(match, updated=())
    def __call__(self, *args, **kwargs) -> typing.Any:
        '''Executes `.match()`, but also checks `.failure`'''
        if (e := self.failure) is not None:
            raise exceptions.NodeNotReadyException(self.name, f'Node {self.name!r} is not ready') from e
        return self.match(*args, **kwargs)

# Nodes
class PatternNode(GrammarNode):
    '''References a pattern'''
    __slots__ = ('failure', 'pname', 'patt')

    pname: str
    patt: re.Pattern | None

    def setup(self, *, patt: str) -> None:
        self.failure = Exception('Node was never compiled')
        self.pname = patt
        self.patt = None

    def compile(self) -> None:
        if not self.bound.patterns.is_complete(self.pname):
            self.failure = ValueError(f'Required pattern {self.pname!r} is missing or incomplete')
            return
        self.patt = re.compile(self.bound.patterns[self.pname])
        self.bound.patterns
        self.failure = None

    def match(self, on: AbstractBufferMatcher) -> tuple[str, re.Match] | None:
        return on(self.patt.match)

class UnionNode(GrammarNode):
    '''References multiple other nodes in a union, matching one of any of them'''
    __slots__ = ('failure', 'nodes')

    nodes: dict[str, GrammarNode | None]

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

    def match(self, on: AbstractBufferMatcher) -> dict | None:
        for name,node in self.nodes.items():
            if (m := node.match(on)) is not None:
                return {'name': name, 'val': m}
        return None
#</Header

#> Package >/
__all__.extend(exceptions.__all__)
from .exceptions import *
__all__ = tuple(__all__)
