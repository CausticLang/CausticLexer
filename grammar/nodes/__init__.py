#!/bin/python3

'''Implements grammar nodes'''

#> Imports
import typing
import functools
from abc import ABC, abstractmethod, abstractproperty
from enum import Enum

from . import exceptions

from .. import __init__ as _root

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

__all__ = ('GrammarNode', 'flat', 'nested') + exceptions.__all__

#> Header
class GrammarNode(ABC):
    '''Base grammar node'''
    __slots__ = ('bound', 'name', 'args', 'return_mode')

    NOMATCH = object()

    @abstractproperty
    @classmethod
    def ReturnMode(cls) -> type[Enum] | None: pass

    bound: '_root.Grammar'
    name: str
    args: tuple[tuple, dict]
    return_mode: Enum | None

    failure: Exception | None = property(lambda _: None)

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
#</Header

#> Package >/
from .exceptions import *

from . import flat
from . import nested
