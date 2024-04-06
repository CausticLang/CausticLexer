#!/bin/python3

'''Nodes that do not really match anything, or behave unlike most nodes'''

#> Imports
import typing

from . import GrammarNode

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('TrueNode', 'FalseNode')

class TrueNode(GrammarNode):
    '''Always matches, returning `val` without consuming anything'''
    __slots__ = ('val',)

    ReturnMode: None = None
    return_mode: None = None

    val: typing.Any

    failure: None = None

    def setup(self, val: typing.Any) -> None:
        if val is self.NOMATCH:
            raise ValueError('val cannot be NOMATCH (maybe you meant to use FalseNode?)')
        self.val = val

    def match(self, on: AbstractBufferMatcher) -> typing.Any:
        return self.val
class FalseNode(GrammarNode):
    '''Never matches'''
    __slots__ = ()

    ReturnMode: None = None
    return_mode: None = None

    failure: None = None

    def match(self, on: AbstractBufferMatcher) -> object:
        return self.NOMATCH
