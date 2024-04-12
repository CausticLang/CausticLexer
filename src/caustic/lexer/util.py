#!/bin/python3

'''Provides small utilites'''

#> Imports
import re
import typing

from . import nodes
#</Imports

#> Header >/
__all__ = ('WHITESPACE_PATT', 'NO_MATCH',
           'bind_nodes')

# Constants
WHITESPACE_PATT = re.compile(rb'\s+')

class NoMatchType:
    __slots__ = ()

    def __new__(cls) -> typing.Self:
        return NO_MATCH
    def __repr__(self) -> str:
        return '<NO_MATCH>'
    def __bool__(self) -> bool:
        return False
NO_MATCH = object.__new__(NoMatchType)
del NoMatchType

# Functions
def bind_nodes(nodes: dict[bytes, 'nodes.Node']) -> None:
    '''Cross-binds all nodes'''
    for node in nodes.values(): node.bind(nodes)
