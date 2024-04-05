#!/bin/python3

'''Implements grammar nodes'''

#> Imports
import re
import typing
import operator
import functools
from abc import ABC, abstractmethod, abstractproperty

from . import exceptions

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

__all__ = ['GrammarNode']

#> Header
# Base node
class GrammarNode(ABC):
    '''Base grammar node'''
    __slots__ = ('bound', 'name', 'args')

    bound: 'nodemgr.NodeManager'
    name: str
    args: tuple[tuple, dict]

    failure: Exception | None = property(lambda _: None)

    def __init__(self, bind: 'nodemgr.NodeManager', name: str, *args, **kwargs):
        self.bound = bind
        self.name = name
        self.args = (args, kwargs)
        if callable(s := getattr(self, 'setup', None)): s(*args, **kwargs)

    def compile(self) -> None:
        '''(Re)compilation callback'''

    @abstractmethod
    def match(self, on: AbstractBufferMatcher) -> dict | None:
        '''Matches on the buffer-matcher `on`, if possible'''

    @functools.wraps(match)
    def __call__(self, *args, **kwargs) -> typing.Any:
        '''Executes `.match()`, but also checks `.failure`'''
        if (e := self.failure) is not None:
            raise exceptions.NodeNotReadyException(self.name, f'Node {self.name!r} is not ready') from e
        return self.match(*args, **kwargs)
#</Header

#> Package >/
__all__.extend(exceptions.__all__)
from .exceptions import *
__all__ = tuple(__all__)
