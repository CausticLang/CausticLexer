#!/bin/python3

'''Provides nodes for matching grammar'''

#> Imports
import io
import re
import typing
from abc import ABCMeta, abstractmethod
from buffer_matcher import SimpleBufferMatcher
from collections import abc as cabc

from .util import WHITESPACE_PATT
from .util import NO_MATCH
#</Imports

#> Header >/
__all__ = ('NodeSyntaxError',
           'Node', 'NodeGroup', 'NodeUnion', 'NodeRange',
           'StringNode', 'PatternNode',
           'Stealer', 'Context', 'NodeRef')

# Exceptions
class NodeSyntaxError(SyntaxError):
    '''For when nodes fail to match something that must be matched'''
    __slots__ = ('node',)

    node: 'Node'
    bm: SimpleBufferMatcher

    def __init__(self, node: 'Node', bm: SimpleBufferMatcher, message: str):
        super().__init__(message)
        self.node = node; self.bm = bm
    def __str__(self) -> str:
        chain = self
        depth = 0
        with io.StringIO() as sio:
            sio.write('Node syntax exception chain (most recent failure last):')
            while chain is not None:
                sio.write(f'\n<{depth}>Node: {chain.node} failed @ {chain.bm.pos} ({chain.bm.lno+1}:{chain.bm.cno})\n')
                sio.write('\n'.join(chain.args))
                for n in getattr(chain, '__notes__', ()):
                    sio.write(f'\nNote: {n}')
                chain = chain.__cause__
                depth += 1
            return sio.getvalue()
# Nodes
## Base
class Node(metaclass=ABCMeta):
    '''The base class for all nodes'''
    __slots__ = ('name',)

    name: str | None

    def __init__(self, *, name: str | None = None):
        self.name = name

    def bind(self, nodes: dict[bytes, typing.Self]) -> None:
        '''Binds all sub-nodes, if possible'''
        if not hasattr(self, 'nodes'): return
        for node in self.nodes: node.bind(nodes)
    def unbind(self) -> None:
        '''Unbinds all sub-nodes'''
        if not hasattr(self, 'nodes'): return
        for node in self.nodes: node.unbind()

    @abstractmethod
    def __call__(self, bm: SimpleBufferMatcher, *, stealer: bool = False) -> object | dict[str, typing.Any]:
        '''Executes this node on `data`'''

    @abstractmethod
    def __str__(self) -> str: pass
    @abstractmethod
    def __repr__(self) -> str: pass

## Groups
class NodeGroup(Node):
    '''
        A group of nodes
        Discards whitespace between nodes if `keep_whitespace` is false
    '''
    __slots__ = ('nodes', 'keep_whitespace')

    nodes: tuple[Node, ...]
    keep_whitespace: bool

    def __init__(self, *nodes: Node, keep_whitespace: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes
        self.keep_whitespace = keep_whitespace

    def __call__(self, bm: SimpleBufferMatcher, stealer: bool = False) -> object | dict[str, typing.Any] | list[typing.Any] | None:
        save = bm.save_pos()
        results = []
        single_result = False
        after = None
        for i,n in enumerate(self.nodes):
            if not self.keep_whitespace:
                bm.match(WHITESPACE_PATT)
            if isinstance(n, Stealer):
                if not i:
                    se = SyntaxError('Cannot have a stealer at the beginning of a group')
                    se.add_note(str(self))
                    raise se
                stealer = True
                after = self.nodes[-1]
                continue
            # Execute node
            try: res = n(bm, stealer=stealer)
            except NodeSyntaxError as nse:
                raise NodeSyntaxError(self, bm, f'Node {i} failed underneath node-group') from nse
            if res is NO_MATCH:
                assert not stealer
                bm.load_pos(save)
                return NO_MATCH
            # Check how we should return results
            if n.name is None: # not assigned a name ("[name]:<node>")
                if isinstance(results, dict): continue # don't add it
                if not single_result: results.append(res)
            elif n.name == '^': # unpack name
                if single_result:
                    te = TypeError(f'Conflicting return types: unpack result cannot be added to single result')
                    te.add_note(str(n))
                    te.add_note(f'In {self}')
                    raise te
                if isinstance(res, dict):
                    if not isinstance(results, dict):
                        results = {}
                    results.update(res)
                elif isinstance(res, cabc.Sequence):
                    if isinstance(results, dict):
                        te = TypeError(f'Conflicting return types: cannot unpack sequence result into named results')
                        te.add_note(str(n))
                        te.add_note(f'In {self}')
                        raise te
                    results.extend(res)
                else:
                    te = TypeError(f'Cannot unpack return {res!r}')
                    te.add_note(str(n))
                    te.add_note(f'In {self}')
                    raise te
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
        return f'{"" if self.name is None else f"{self.name}:"}{"({"[self.keep_whitespace]} {" ".join(map(str, self.nodes))} {")}"[self.keep_whitespace]}'
    def __repr__(self) -> str:
        return f'<{type(self).__qualname__} {self.name!r}{" [keep_whitespace]" if self.keep_whitespace else ""} {self.nodes!r}>'

class NodeUnion(Node):
    '''Matches any of its nodes'''
    __slots__ = ('nodes',)

    nodes: tuple[Node, ...]

    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes

    def __call__(self, bm: SimpleBufferMatcher, *, stealer: bool = False) -> object | dict[str, typing.Any]:
        for n in self.nodes:
            if (res := n(bm)) is not NO_MATCH:
                return res
        if stealer: raise NodeSyntaxError(self, bm, f'Expected union {self}')
        return NO_MATCH

    def __str__(self) -> str:
        return f'{"" if self.name is None else f"{self.name}:"}[ {" ".join(map(str, self.nodes))} ]'
    def __repr__(self) -> str:
        return f'<{type(self).__qualname__} {self.name!r} {self.nodes!r}>'

    @classmethod
    def from_kwargs(cls, kwargs: dict) -> typing.Self:
        return cls(*kwargs['nodes'], name=kwargs['name'])

class NodeRange(Node):
    '''
        Matches between `min` and `max` nodes,
            or any amount over `min` if `max` is `None`
    '''
    __slots__ = ('min', 'max', 'node', 'keep_whitespace')

    def __init__(self, node: Node, min: int | None, max: int | None, *, keep_whitespace: bool = False, **kwargs):
        super().__init__(**kwargs)
        if min is None: min = 0
        else: assert min >= 0, 'min should not be negative'
        assert (max is None) or (max >= 0), 'max should be None or more than or equal to min'
        self.min = min
        self.max = max
        self.node = node
        self.keep_whitespace = keep_whitespace

    def bind(self, nodes: dict[bytes, Node]) -> bool | None:
        '''Binds the underlying node, if applicable'''
        return self.node.bind(nodes)

    def __call__(self, bm: SimpleBufferMatcher, *, stealer: bool = False) -> object | list[typing.Any]:
        results = []
        save = bm.save_pos()
        for _ in range(self.min):
            try: results.append(self.node(bm, stealer=stealer))
            except NodeSyntaxError as nse:
                raise NodeSyntaxError(self, bm, f'Expected at least {self.min} of {self.node}') from nse
            if results[-1] is NO_MATCH:
                bm.load_pos(save)
                return NO_MATCH
            if not self.keep_whitespace:
                bm.match(WHITESPACE_PATT)
        if self.max is None:
            while (res := self.node(bm)) is not NO_MATCH:
                results.append(res)
                if not self.keep_whitespace:
                    bm.match(WHITESPACE_PATT)
        else:
            for _ in range(self.min, self.max):
                res = self.node(bm)
                if res is NO_MATCH: break
                results.append(res)
                if not self.keep_whitespace:
                    bm.match(WHITESPACE_PATT)
        return results

    def __str__(self) -> str:
        return f'{self.min or ""}-{"" if self.max is None else {self.max}} {self.node}'
    def __repr__(self) -> str:
        return f'<{type(self).__qualname__} {self.name!r} {" [keep_whitespace]" if self.keep_whitespace else ""}{self.min!r} - {self.max!r}>'

## Real
class StringNode(Node):
    '''Matches a specific string'''
    __slots__ = ('string',)

    string: bytes

    def __init__(self, string: bytes, **kwargs):
        super().__init__(**kwargs)
        self.string = string
        if not self.string:
            raise ValueError('Cannot use an empty string')

    def __call__(self, bm: SimpleBufferMatcher, *, stealer: bool = False) -> object | bytes:
        if bm.match(self.string):
            return self.string
        if stealer:
            raise NodeSyntaxError(self, bm, f'Expected string {self}')
        return NO_MATCH

    def __str__(self) -> str:
        return f'"{"" if self.name is None else f"{self.name}:"}{self.string.decode(errors="backslashreplace").replace("\"", "\\\"")}"'
    def __repr__(self) -> str:
        return f'<{type(self).__qualname__} {self.name!r} {self.string!r}>'
class PatternNode(Node):
    '''Matches a pattern (regular expression)'''
    __slots__ = ('pattern', 'group')

    group: int | None
    pattern: re.Pattern

    def __init__(self, pattern: re.Pattern, group: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self.pattern = pattern
        self.group = group

    def __call__(self, bm: SimpleBufferMatcher, *, stealer: bool = False) -> object | re.Match | bytes:
        if (m := bm.match(self.pattern)) is not None:
            return m.group(self.group) if self.group is not None else m
        if stealer:
            raise NodeSyntaxError(self, bm, f'Expected pattern {self}')
        return NO_MATCH

    FLAGS = {'i': re.IGNORECASE, 'm': re.MULTILINE, 's': re.DOTALL}
    def __str__(self) -> str:
        return (f'{"" if self.name is None else f"{self.name}:"}'
                f'{"" if self.group is None else self.group}/'
                f'{self.pattern.pattern.decode(errors="backslashreplace").replace("/", "\\/")}/'
                f'{"".join(f for f,v in self.FLAGS.items() if v & self.pattern.flags)}')
    def __repr__(self) -> str:
        return f'<{type(self).__qualname__} {self.pattern!r}{"" if self.group is None else f"[{self.group}]"}>'

## Meta
class Stealer(Node):
    '''Marks a special "stealer" node'''
    __slots__ = ()

    def __call__(self, *args, **kwargs):
        raise TypeError(f'Stealer nodes should not be called')

    def __str__(self) -> str: return '!'
    def __repr__(self) -> str: return f'<{type(self).__qualname__}>'
class Context(Node):
    '''Marks a special "context" node that always matches'''
    __slots__ = ('val',)

    val: typing.Any

    def __init__(self, val: typing.Any, **kwargs):
        assert val is not NO_MATCH, 'Cannot use NO_MATCH marker object for Context val'
        super().__init__(**kwargs)
        self.val = val

    def __call__(self, bm: SimpleBufferMatcher, *, stealer: bool = False) -> typing.Any:
        return self.val

    def __str__(self) -> str:
        return f'{"" if self.name is None else f"{self.name}:"}< {self.val} >'
    def __repr__(self) -> str:
        return f'<{type(self).__qualname__}>'
class NodeRef(Node):
    '''Marks a special "reference" node that "includes" another node'''
    __slots__ = ('target_name', 'target')

    target_name: bytes
    target: Node | None

    def __init__(self, target: bytes, **kwargs):
        super().__init__(**kwargs)
        self.target_name = target
        self.target = None

    @property
    def bound(self) -> bool: return self.target is not None
    def bind(self, targets: dict[bytes, Node]) -> bool:
        '''
            Attempts to bind this node to nodes in a dict
            If `.target_name` is not found in the dict, `False` is returned,
                otherwise `.target` is set to that node and `True` is returned
            Note: if this node was previously bound, that binding is removed,
                even if rebinding fails
        '''
        self.target = targets.get(self.target_name)
        return self.target is not None
    def unbind(self) -> None:
        '''Unbinds this node'''
        self.target = None

    def __call__(self, bm: SimpleBufferMatcher, *, stealer: bool = False) -> typing.Any:
        if not self.bound:
            raise TypeError(f'Cannot call an unbound NodeRef (node target {self.target_name} was never bound)')
        try: return self.target(bm, stealer)
        except NodeSyntaxError as nse:
            nse.add_note(f'Under reference {self}')
            raise nse

    def __str__(self) -> str:
        return f'@{self.target_name!r}'
    def __repr__(self) -> str:
        return (f'<{type(self).__qualname__} {self.name!r} target:{self.target_name!r} '
                f'{"[unbound]" if self.target is None else repr(self.target)}>')
