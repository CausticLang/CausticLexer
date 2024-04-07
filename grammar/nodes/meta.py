#!/bin/python3

'''Nodes that do not really match anything, or behave unlike most nodes'''

#> Imports
import typing

from . import base

from . import GrammarMark

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('TrueNode', 'FalseNode', 'NotNode')

class TrueNode(base.NeverNestedNode):
    '''Always matches, returning `val` without consuming anything'''
    __slots__ = ('val',)

    BASE_COMPILE_ORDER_HINT = -900

    ReturnMode: None = None
    return_mode: None = None

    val: typing.Any

    failure: None
    
    def setup(self, *, val: typing.Any, **kwargs) -> None:
        super().setup(**kwargs)
        if isinstance(val, GrammarMark):
            raise TypeError('val cannot be a GrammarMark')
        self.val = val

    def match(self, on: AbstractBufferMatcher) -> typing.Any:
        return self.val
class FalseNode(base.NeverNestedNode):
    '''Never matches'''
    __slots__ = ()

    BASE_COMPILE_ORDER_HINT = -900

    def match(self, on: AbstractBufferMatcher) -> GrammarMark:
        return GrammarMark.NO_MATCH

class NotNode(base.SingleNestedNode):
    '''
        Only matches (returning `val`) if the given node `node` does not match
        Note: backtracks if the given node does match
    '''
    __slots__ = ('failure', 'val')

    val: typing.Any

    def setup(self, *, val: typing.Any, **kwargs) -> None:
        super().setup(**kwargs)
        if isinstance(val, GrammarMark):
            raise TypeError('val cannot be a GrammarMark')
        self.val = val

    def match(self, on: AbstractBufferMatcher) -> GrammarMark | typing.Any:
        save = on.save_loc()
        if self.node(on) is GrammarMark.NO_MATCH:
            return self.val # -> typing.Any
        on.load_loc(save) # backtrack
        return GrammarMark.NO_MATCH # -> GrammarMark
