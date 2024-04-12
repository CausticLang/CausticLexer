#!/bin/python3

'''Provides small utilites'''

#> Imports
from . import nodes
#</Imports

#> Header >/
__all__ = ('bind_nodes',)

def bind_nodes(nodes: dict[bytes, nodes.Node]) -> None:
    '''Cross-binds all nodes'''
    for node in nodes.values(): node.bind(nodes)
