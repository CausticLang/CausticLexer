#!/bin/python3

'''Provides the framework for Caustic's grammar management'''

#> Imports
import operator
from collections import abc as cabc
#</Imports

__all__ = ('nodes', 'loaders', 'buffer_matcher', 'Grammar')

#> Package
from . import nodes # re-exposed
from . import loaders # re-exposed
from . import buffer_matcher # re-exposed
#</Package

#> Header >/
class Grammar:
    '''Holds grammar for both nodes and patterns'''
    __slots__ = ('nodes', 'patterns')

    nodes: dict[str, nodes.GrammarNode]
    patterns: loaders.pattern.PatternLoader

    def __init__(self, *, nodes: dict[str, nodes.GrammarNode | None] = None,
                 patts: loaders.pattern.PatternLoader | type[loaders.pattern.PatternLoader] | None = None):
        self.patterns = (loaders.pattern.PatternLoader() if patts is None
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

    def add_node(self, node: nodes.GrammarNode, /,*, replace: bool = False,
                 bind: bool = True, compile: bool = True, **kwargs) -> nodes.GrammarNode:
        '''
            Adds a node, using its name as its key

            Raises a `NodeExistsError` if the node already exists, unless `replace`

            Binds the node to this `Grammar` with `node.bind()` if `bind`

            If `compile`, then `.compile()` (`Grammar.compile()`, not `node.compile()`)
                is executed after adding it, with `needed` being true unless the node replaced
                another node, in which case all nodes should be recompiled in case any
                node depended upon that node
                It is recommended to set `compile` to false when adding many nodes,
                    and to manually run `.compile()` after they are added to prevent over-recompilation

            Returns the passed node to allow chaining
        '''
        exists = node.name in self.nodes
        if exists and (not replace):
            raise nodes.NodeExistsError(f'Node with name {node.name!r} is already registered')
        self.nodes[node.name] = node
        if bind: node.bind(self)
        if compile: self.compile(needed=exists)
        return node
    def pop_node(self, node: nodes.GrammarNode | str, *, ignore_missing: bool = False, compile: bool = True) -> nodes.GrammarNode:
        '''
            Removes and returns a node
                Note that the node will still be bound to this `Grammar`

            Raises `NodeMissingError` if the node is missing unless `ignore_missing`

            If `compile`, then `.compile()` will be run after removing the node
                Note that `.compile()` will not be run if the node is missing
        '''
        name = node if isinstance(node, str) else node.name
        if name not in self.nodes:
            if ignore_missing: return
            raise nodes.NodeMissingError(f'Node {node!r} (name {name!r}) is missing')
        node = self.pop(name)
        if compile: self.compile()
        return node
