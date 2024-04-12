#!/bin/python3

'''Provides small utilites'''

#> Imports
import re

from . import nodes
#</Imports

#> Header >/
__all__ = ('WHITESPACE_PATT',
           'bind_nodes')

# Constants
WHITESPACE_PATT = re.compile(rb'\s+')

# Functions
def bind_nodes(nodes: dict[bytes, nodes.Node]) -> None:
    '''Cross-binds all nodes'''
    for node in nodes.values(): node.bind(nodes)
