#!/bin/python3

'''Provides nodes for matching grammar'''

#> Imports
import io
import re
import typing
from abc import ABCMeta, abstractmethod
from buffer_matcher import SimpleBufferMatcher
#</Imports

__all__ = ('NodeSyntaxError',
           'Node', 'NodeGroup', 'NodeUnion', 'NodeRange',
           'StringNode', 'PatternNode',
           'Stealer', 'Context', 'NodeRef')

#> Header >/
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
            while chain is not None:
                sio.write(f'\n<{depth}>Node: {chain.node} failed @ {chain.bm.pos} ({chain.bm.lno+1}:{chain.bm.cno})\n')
                sio.write('\n'.join(chain.args))
                chain = chain.__cause__
                depth += 1
            return sio.getvalue().strip('\n')
# Nodes
## Base
class Node(metaclass=ABCMeta):
    '''The base class for all nodes'''
    __slots__ = ('name',)

    NO_RETURN = object()

    name: str | None

    def __init__(self, *, name: str | None = None):
        self.name = name

    def bind(self, nodes: dict[bytes, typing.Self]) -> None:
        '''Binds all sub-nodes, if possible'''
        if not hasattr(self, 'nodes'): return
        for node in self.nodes: node.bind(nodes)

    @abstractmethod
    def __call__(self, bm: SimpleBufferMatcher) -> object | dict[str, typing.Any]:
        '''Executes this node on `data`'''
    @abstractmethod
    def __str__(self) -> str: pass
    def __repr__(self) -> str: return str(self)

## Groups
class NodeGroup(Node):
    '''
        A group of nodes
        Discards whitespace between nodes if `keep_whitespace` is false
    '''
    __slots__ = ('nodes', 'keep_whitespace')

    nodes: tuple[Node, ...]
    keep_whitespace: bool

    WHITESPACE_PATT = re.compile(rb'\s+')

    def __init__(self, *nodes: Node, keep_whitespace: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes
        self.keep_whitespace = keep_whitespace

    def __call__(self, bm: SimpleBufferMatcher) -> object | dict[str, typing.Any] | list[typing.Any] | None:
        save = bm.save_pos()
        results = []
        single_result = False
        stealer = False; after = None
        for i,n in enumerate(self.nodes):
            if not self.keep_whitespace:
                bm.match(self.WHITESPACE_PATT)
            if isinstance(n, Stealer):
                if not i:
                    se = SyntaxError('Cannot have a stealer at the beginning of a group')
                    se.add_note(str(self))
                    raise se
                stealer = True
                after = self.nodes[-1]
                continue
            # Execute node
            try: res = n(bm)
            except NodeSyntaxError as nse:
                raise NodeSyntaxError(self, bm, f'Node {i} failed underneath node-group{f"\n After: {self.nodes[i-1]}" if i else ""}') from nse
            if res is self.NO_RETURN:
                if not stealer:
                    bm.load_pos(save)
                    return self.NO_RETURN
                nse = NodeSyntaxError(self, bm, f'Node {i} failed underneath node-group {f"\n After: {self.nodes[i-1]}" if i else ""}')
                nse.add_note(f'Note: stealer defined after node {after}')
                raise nse from NodeSyntaxError(n, bm, 'Node failed to match')
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
        return f'{"" if self.name is None else f"{self.name}:"}{"({"[self.keep_whitespace]} {" ".join(map(str, self.nodes))} {")}"[self.keep_whitespace]}'

class NodeUnion(Node):
    '''Matches any of its nodes'''
    __slots__ = ('nodes',)

    nodes: tuple[Node, ...]

    def __init__(self, *nodes: Node, **kwargs):
        super().__init__(**kwargs)
        self.nodes = nodes

    def __call__(self, bm: SimpleBufferMatcher) -> object | dict[str, typing.Any]:
        for n in self.nodes:
            if (res := n(bm)) is not self.NO_RETURN:
                return res
        return self.NO_RETURN

    def __str__(self) -> str:
        return f'{"" if self.name is None else f"{self.name}:"}[ {" ".join(map(str, self.nodes))} ]'

class NodeRange(Node):
    '''
        Matches between `min` and `max` nodes,
            or any amount over `min` if `max` is `None`
    '''
    __slots__ = ('min', 'max', 'node')

    def __init__(self, node: Node, min: int | None, max: int | None, **kwargs):
        super().__init__(**kwargs)
        if min is None: min = 0
        else: assert min >= 0, 'min should not be negative'
        assert (max is None) or (max >= 0), 'max should be None or more than or equal to min'
        self.min = min
        self.max = max
        self.node = node

    def bind(self, nodes: dict[bytes, Node]) -> bool | None:
        '''Binds the underlying node, if applicable'''
        return self.node.bind(nodes)

    def __call__(self, bm: SimpleBufferMatcher) -> object | list[typing.Any]:
        results = []
        save = bm.save_pos()
        for _ in range(self.min):
            results.append(self.node(bm))
            if results[-1] is self.NO_RETURN:
                self.load_pos()
                return self.NO_RETURN
        if self.max is None:
            while (res := self.node(bm)) is not self.NO_RETURN:
                results.append(res)
        else:
            for _ in range(self.min, self.max):
                res = self.node(bm)
                if res is self.NO_RETURN: break
                results.append(res)
        return results

    def __str__(self) -> str:
        return f'{self.min or ""}.{"" if self.max is None else {self.max}}~ {self.node}'

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

    def __call__(self, bm: SimpleBufferMatcher) -> object | bytes:
        if bm.match(self.string):
            return self.string
        return self.NO_RETURN

    def __str__(self) -> str:
        return f'"{"" if self.name is None else f"{self.name}:"}{self.string.decode(errors="backslashreplace").replace("\"", "\\\"")}"'
class PatternNode(Node):
    '''Matches a pattern (regular expression)'''
    __slots__ = ('pattern', 'group')

    group: int | None
    pattern: re.Pattern

    def __init__(self, pattern: re.Pattern, group: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self.pattern = pattern
        self.group = group

    def __call__(self, bm: SimpleBufferMatcher) -> object | re.Match | bytes:
        if (m := bm.match(self.pattern)) is not None:
            return m.group(self.group) if self.group else m
        return self.NO_RETURN

    FLAGS = {'i': re.IGNORECASE, 'm': re.MULTILINE, 's': re.DOTALL}
    def __str__(self) -> str:
        return (f'{"" if self.name is None else f"{self.name}:"}'
                f'{"" if self.group is None else self.group}/'
                f'{self.pattern.pattern.decode(errors="backslashreplace").replace("/", "\\/")}/'
                f'{"".join(f for f,v in self.FLAGS.items() if v & self.pattern.flags)}')

## Meta
class Stealer(Node):
    '''Marks a special "stealer" node'''
    __slots__ = ()

    def __call__(self, *args, **kwargs):
        raise TypeError(f'Stealer nodes should not be called')

    def __str__(self) -> str: return '!'
class Context(Node):
    '''Marks a special "context" node that always matches'''
    __slots__ = ('val',)

    val: typing.Any

    def __init__(self, val: typing.Any, **kwargs):
        assert val is not self.NO_RETURN, 'Cannot use NO_RETURN marker object for Context val'
        super().__init__(**kwargs)
        self.val = val

    def __call__(self, bm: SimpleBufferMatcher) -> typing.Any:
        return self.val

    def __str__(self) -> str: return f'{"" if self.name is None else f"{self.name}:"}< {self.val} >'
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

    def __call__(self, bm: SimpleBufferMatcher):
        if not self.bound:
            raise TypeError(f'Cannot call an unbound NodeRef (node target {self.target_name} was never bound)')
        return self.target(bm)

    def __str__(self) -> str:
        return f'@{self.target_name!r}'
