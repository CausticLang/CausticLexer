#!/bin/python3

'''Nodes that do not really match anything, or behave unlike most nodes'''

#> Imports
import typing

from . import GrammarNode

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('TrueNode', 'FalseNode', 'NotNode')

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

class NotNode(GrammarNode):
    '''
        Only matches (returning `val`) if the given node does not match
        Note: backtracks if the given node does match
    '''
    __slots__ = ('failure', 'node_name', 'node', 'val')

    ReturnMode: None = None
    return_mode: None = None

    node_name: str
    node: GrammarNode | None
    val: typing.Any

    def setup(self, node: str, val: typing.Any) -> None:
        self.failure = Exception('Node was never compiled')
        self.node_name = node
        if val is self.NOMATCH:
            raise ValueError('val cannot be NOMATCH')
        self.val = val

    def compile(self) -> None:
        if self.node_name not in self.bound.nodes:
            self.failure = KeyError(f'Required node {node!r} is missing')
            return
        self.node = self.bound.nodes[self.node_name]
        if self.node.failure is not None:
            self.failure = ValueError(f'Required node {node!r} failed to compile')
            self.failure.__context__ = self.node.failure
        self.failure = None

    def match(self, on: AbstractBufferMatcher) -> object | typing.Any:
        save = on.save_loc()
        if self.node(on) is self.NOMATCH:
            return self.val # -> typing.Any
        on.load_loc(save) # backtrack
        return self.NOMATCH # -> object
