#!/bin/python3

#> Imports
import io
import re
import typing
from abc import ABCMeta, abstractmethod

import buffer_matcher
#</Imports

__all__ = ('NodeSyntaxError',
           'Node', 'NodeGroup', 'NodeUnion',
           'StringNode', 'PatternNode')

#> Header >/
# Exceptions
class NodeSyntaxError(SyntaxError):
    __slots__ = ('node',)

    node: 'Node'
    bm: buffer_matcher.AbstractBufferMatcher

    def __init__(self, node: 'Node', bm: buffer_matcher.AbstractBufferMatcher, message: str):
        super().__init__(message)
        self.node = node; self.bm = bm
    def __str__(self) -> str:
        chain = self
        with io.StringIO() as sio:
            while chain is not None:
                sio.write(f'\nNode: {self.node} failed @ {self.bm.pos} ({self.bm.lno+1}:{self.bm.cno})\n')
                sio.write('\n'.join(self.args))
                chain = chain.__context__
            return sio.getvalue().strip('\n')
# Nodes
class Node(metaclass=ABCMeta):
    '''The base class for all nodes'''
    __slots__ = ('name', 'is_stealer')

    NO_RETURN = object()

    name: str | None
    is_stealer: bool

    def __init__(self, *, name: str | None = None, is_stealer: bool = False):
        self.name = name
        self.is_stealer = is_stealer

    @abstractmethod
    def __call__(self, bm: buffer_matcher.AbstractBufferMatcher) -> object | dict[str, typing.Any]:
        '''Executes this node on `data`'''
    @abstractmethod
    def __str__(self) -> str: pass

class NodeGroup(Node):
    '''A group of nodes'''
    __slots__ = ('nodes', 'ignore_whitespace')

    nodes: tuple[Node, ...]
    ignore_whitespace: bool

    def __init__(self, *nodes: Node, ignore_whitespace: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes
        self.ignore_whitespace = ignore_whitespace
    def __call__(self, bm: buffer_matcher.AbstractBufferMatcher) -> object | dict[str, typing.Any] | list[typing.Any] | None:
        save = bm.save_loc()
        results = []
        single_result = False
        for i,n in enumerate(self.nodes):
            # Execute node
            try: res = n(bm)
            except NodeSyntaxError:
                raise NodeSyntaxError(self, bm, f'Node failed underneath node-group{f"\n After: {self.nodes[i-1]}" if i else ""}')
            if res is self.NO_RETURN:
                if not self.is_stealer:
                    bm.load_loc(save)
                    return self.NO_RETURN
                raise NodeSyntaxError(self, bm, f'Node failed underneath node-group{f"\n After: {self.nodes[i-1]}" if i else ""}') \
                      from NodeSyntaxError(n, bm, 'Non-stealer node failed, but caused node-group to fail')
            # Check how we should return results
            if n.name is None: # not assigned a name ("[name]:<node>")
                if isinstance(results, dict): continue # don't add it
                if not single_result: results.append(res)
            elif n.name: # name is not blank ("<name>:<node>")
                if isinstance(results, dict):
                    results[n.name] = res
                elif single_result:
                    te = TypeError(f'Conflicting return types: named result {n.name} cannot be added to single result')
                    te.add_note(str(n))
                    te.add_note(f'In {self}')
                    raise te
                else:
                    results = {n.name: res}
            else: # name is blank (":<node>")
                if isinstance(results, dict):
                    te = TypeError('Conflicting return types: single result cannot be added to named results')
                    te.add_note(str(n))
                    te.add_note(f'In {self}')
                    raise te
                single_result = True
                results = res
        if not results: return None
        return results
    def __str__(self) -> str:
        return f'{"({"[self.ignore_whitespace]} {" ".join(map(str, self.nodes))}{")}"[self.ignore_whitespace]}{"!" if self.is_stealer else ""}'

class NodeUnion(Node):
    '''Matches any of its nodes'''
    __slots__ = ('nodes',)

    nodes: tuple[Node, ...]

    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes
    def __call__(self, bm: buffer_matcher.AbstractBufferMatcher) -> object | dict[str, typing.Any]:
        for n in self.nodes:
            if (res := n(bm)) is not self.NO_RETURN:
                return res
        if not self.is_stealer: return self.NO_RETURN
        raise NodeSyntaxError('No nodes matched')
    def __str__(self) -> str:
        return f'[ {" ".join(map(str, self.nodes))} ]{"!" if self.is_stealer else ""}'

class StringNode(Node):
    '''Matches a specific string'''
    __slots__ = ('string',)

    string: bytes

    def __init__(self, string: bytes, **kwargs):
        super().__init__(**kwargs)
        self.string = string
    def __call__(self, bm: buffer_matcher.AbstractBufferMatcher) -> object | bytes:
        if bm.peek(len(self.string)) == self.string:
            return bytes(bm.step(len(self.string)))
        if not self.is_stealer: return self.NO_RETURN
        raise NodeSyntaxError(self, bm, 'Expected string')
    def __str__(self) -> str:
        return f'"{self.string.decode(errors="backslashreplace").replace("\"", "\\\"")}"{"!" if self.is_stealer else ""}'
class PatternNode(Node):
    '''Matches a pattern (regular expression)'''
    __slots__ = ('pattern',)

    pattern: re.Pattern

    def __init__(self, pattern: re.Pattern, **kwargs):
        self.pattern = pattern
    def __call__(self, bm: buffer_matcher.AbstractBufferMatcher) -> object | re.Match:
        ...
