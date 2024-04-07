#!/bin/python3

'''Provides the framework for Caustic's grammar management'''

#> Imports
import operator
from collections import abc as cabc
#</Imports

__all__ = ('nodes', 'patterns', 'Grammar')

#> Package
from . import nodes # re-exposed
from . import patterns # re-exposed
#</Package

#> Header >/
class Grammar:
    '''Holds grammar for both nodes and patterns'''
    __slots__ = ('nodes', 'patterns')

    nodes: dict[str, nodes.GrammarNode]
    patterns: patterns.PatternLoader

    def __init__(self, *, nodes: dict[str, nodes.GrammarNode | None] = None,
                 patts: patterns.PatternLoader | type[patterns.PatternLoader] | None = None):
        self.patterns = (patterns.PatternLoader() if patts is None
                         else patterns() if isinstance(patterns, type) else patterns)
        self.nodes = ({} if nodes is None else nodes)

    def node_stat(self, nodes: cabc.Sequence[str] | None = None) -> tuple[frozenset[str], frozenset[str]]:
        '''
            Returns a tuple of two frozensets,
                with the first being names of nodes that have no `.failure`,
                and the second being names of nodes that have `.failure`
        '''
        nodes = frozenset(self.nodes.keys() if nodes is None else nodes)
        succs = frozenset((n for n in nodes if self.nodes[n].failure is None))
        return (succs, nodes - succs)

    def compile(self, nodes: cabc.Sequence[str] | None = None, *, needed: bool = True) -> frozenset[str]:
        '''
            Compiles nodes, returning a frozenset of node names that failed compilation
            If `needed` is true, then only compiles nodes that have failed to compile
        '''
        nodes = frozenset(self.nodes.keys() if nodes is None else nodes)
        if needed:
            nodes = frozenset(filter(lambda k: self.nodes[k].failure is not None, nodes))
        prev_succ = -1
        successes = set()
        while prev_succ != (prev_succ := len(successes)):
            for node in sorted(map(self.nodes.__getitem__, nodes - successes),
                               key=operator.attrgetter('compile_order_hint')):
                assert self.nodes[node.name] is node
                node.compile()
                if node.failure is None:
                    successes.add(node.name)
                else:
                    node.compile_order_hint += 1
        return nodes - successes
