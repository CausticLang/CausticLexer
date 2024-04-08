#!/bin/python3

'''Base `GrammarNode`, as well as mixins'''

#> Imports
import typing
import inspect
from abc import ABCMeta, abstractmethod, abstractproperty
from enum import Enum
from collections import abc as cabc

from . import exceptions

from . import GrammarMark

from .. import __init__ as _root

from ..buffer_matcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('GrammarNode',
           'NodeWithReturnMode',
           'NeverNestedNode', 'SingleNestedNode', 'MultiNestedNode')

class GrammarNode(metaclass=ABCMeta):
    '''
        The base grammar node
        Note that subclasses can define `.init_x()` methods (`x` is sorted alphabetically),
            and each method will be called in order by `__init__()`
            with its keyword arguments fulfilled (sourcing from `inspect.getargs`) by parts of `kwargs`
    '''
    __slots__ = (# common
                 'compile_order_hint',
                 'bound', 'name', 'args', 'failure',
                 # specific to other base types (prevent instance lay-out conflict)
                 'return_mode', 'node_name', 'node', 'nodes')

    #PRE_SETUPS: typing.ClassVar[tuple[cabc.Callable, ...]] = ()
    #SETUPS: typing.ClassVar[tuple[tuple[cabc.Callable, frozenset[str], bool], ...]] = ()

    BASE_COMPILE_ORDER_HINT: typing.ClassVar[int] = 0
    compile_order_hint: int

    bound: typing.ForwardRef('_root.Grammar') | None
    name: str
    args: dict[str, typing.Any]

    failure: Exception | None

    #def __init_subclass__(cls):
    #    targets = (mro := cls.mro())[:mro.index(GrammarNode)]
    #    cls.PRE_SETUPS = tuple(filter(None, (c.__dict__.get('pre_setup', None) for c in targets)))
    #    cls.SETUPS = tuple(
    #        (fn, (args := inspect.getargs(fn.__code__)).args, (args.varkw is not None))
    #        for fn in ((c.__dict__.get('setup', None)) for c in targets) if fn is not None)
    def __init__(self, name: str, *, bind: typing.ForwardRef('_root.Grammar') | None = None, **kwargs: typing.Any):
        self.compile_order_hint = self.BASE_COMPILE_ORDER_HINT
        self.bound = bind
        self.name = name
        self.args = kwargs
        self.failure = None
        # execute pre_setup()s and setup()s
        #self.exec_pre_setups()
        self.pre_setup()
        #self.exec_setups(kwargs.copy())
        self.setup(**kwargs)

    def bind(self, to: '_root.Grammar', *, compile: bool = True) -> None:
        '''Binds the node to `to`, compiling it if `compile`'''
        self.bound = to
        if compile: self.compile()
    def unbind(self, *, compile: bool = True) -> None:
        '''Unbinds the node, recompiling it if `compile`'''
        self.bound = None
        if compile: self.compile()

    #def exec_pre_setups(self) -> None:
    #    '''Execute all `.pre_setup()` functions'''
    #    for f in self.PRE_SETUPS: f(self)
    #def exec_setups(self, kwargs: dict[str, typing.Any]) -> None:
    #    '''
    #        Execute all `.setup()` functions
    #        Automatically passes `kwargs` to the functions that take them
    #            Note that `kwargs` is mutated
    #    '''
    #    for f,args,varkw in self.SETUPS:
    #        if not varkw:
    #            f(self, **{k: kwargs.pop(k) for k in args & kwargs.keys()})
    #            continue
    #        f(self, **kwargs)
    #        kwargs.clear()
    #    if kwargs:
    #        raise TypeError(f'Extraneous keyword arguments in .exec_setups(): {", ".join(kwargs.keys())}')

    def pre_setup(self) -> None:
        '''
            Executed during initialization before `.setup()`
            All `.pre_setup()` in the MRO (up to, not including, `GrammarNode`) are executed
        '''
    def setup(self) -> None:
        '''
            Executed during initialization and passed `**kwargs`
            All `.setup()` in the MRO (up to, not including, `GrammarNode`) are executed,
                with passed kwargs automatically being used in the correct setup
        '''

    def check_unbound(self) -> bool:
        '''
            Utility function for subclasses,
                sets a failure and returns true if the node is unbound
        '''
        if self.bound is None:
            self.failure = ReferenceError(f'Node {self!r} is unbound')
            return True
        return False

    def compile(self) -> None:
        '''Attempts to compile the node, setting failure to `.failure`'''

    def check(self, for_match: bool = False) -> None:
        '''Raises exceptions if the node is not ready'''
        if not for_match: return
        if (e := self.failure) is not None:
            raise exceptions.NodeNotReadyException(self.name, f'Node {self!r} is not ready') from e
    @abstractmethod
    def match(self, on: AbstractBufferMatcher) -> GrammarMark | typing.Any:
        '''
            Matches with the buffer-matcher `on`
            **Does *not* execute any checks, use `__call__`**
        '''
    def __call__(self, on: AbstractBufferMatcher, **kwargs) -> GrammarMark | typing.Any:
        '''Matches with the buffer-matcher `on`, but runs `.check()` first'''
        self.check(**kwargs, for_match=True)
        return self.match(on, **kwargs)

    def __repr__(self) -> str:
        return (f'<{type(self).__name__} {self.name!r}'
                f'({", ".join(f"{k}={v!r}" for k,v in self.args.items())})>')

# Mixins
class NodeWithReturnMode(GrammarNode):
    '''Adds a configurable return mode'''
    __slots__ = ()

    @abstractproperty
    @classmethod
    def ReturnMode(cls) -> type[Enum]: pass
    return_mode: Enum | None

    def setup(self, *, return_mode: Enum | None = None, **kwargs) -> None:
        super().setup(**kwargs)
        self.check(return_mode)
        self.return_mode = return_mode

    def check(self, return_mode: Enum | None = None, **kwargs) -> None:
        super().check(**kwargs)
        if ((return_mode is None) or
            isinstance(return_mode, self.ReturnMode)): return
        raise TypeError(f'return_mode should be a {self.ReturnMode}, got {return_mode!r}')

    def __call__(self, on: AbstractBufferMatcher, *, return_mode: Enum | None = None, **kwargs) -> GrammarMark | typing.Any:
        super().__call__(on, return_mode=(self.return_mode if return_mode is None
                                          else return_mode), **kwargs)

# Nesting
class NeverNestedNode(GrammarNode):
    '''
        A mixin grammar node for nodes that will never require
            any other nodes to be compiled before its own compilation

        Marks this node for earlier compilation than `GrammarNode`
    '''
    __slots__ = ()

    BASE_COMPILE_ORDER_HINT = -100

class SingleNestedNode(GrammarNode):
    '''
        A mixin grammar node for nodes that require a single other node

        Marks this node for later compilation than `GrammarNode` to
            potentially reduce recompilation attempts
    '''
    __slots__ = ()

    BASE_COMPILE_ORDER_HINT = 100

    def pre_setup(self) -> None:
        super().pre_setup()
        self.failure = exceptions.NodeNotReadyException(self.name,
            'This node requires a sub-node, but has not been compiled')
    def setup(self, *, node: str, **kwargs) -> None:
        super().setup(**kwargs)
        self.node_name = node

    def check_node(self: GrammarNode, name: str) -> GrammarNode | None:
        '''Utility method for checking a node, setting `.failure` appropriately'''
        node = self.bound.nodes.get(name, None)
        if node.check_unbound(): return None
        if node.failure is not None:
            self.failure = exceptions.DependencyNodeNotReadyError(name, f'Required node {name!r} is not ready')
            self.failure.__context__ = node.failure
            return None
        return node
    def compile(self) -> None:
        '''Attempts to compile this node against the contained node'''
        self.failure = None
        if self.check_unbound(): return
        self.node = self.check_node(self.node_name)
class MultiNestedNode(GrammarNode):
    '''
        A mixin grammar node for nodes that require multiple other nodes

        Marks this node for later compilation than `GrammarNode` and `NestedSingleNode` to
            potentially reduce recompilation attempts
    '''
    __slots__ = ()

    BASE_COMPILE_ORDER_HINT = 200

    def pre_setup(self) -> None:
        super().pre_setup()
        self.failure = exceptions.NodeNotReadyException(self.name,
            'This node requires sub-nodes, but has not been compiled')
    def setup(self, *, nodes: cabc.Iterable[str, ...], **kwargs) -> None:
        super().setup(**kwargs)
        self.nodes = dict.fromkeys(nodes, None)
        if not self.nodes:
            raise TypeError(f'Cannot setup MultiNestedNode {self!r} with no nodes')
        self.compile_order_hint += 10 * len(nodes)

    def check_nodes(self, *names: str) -> None:
        '''
            Utility method for checking nodes, setting `.failure` appropriately
            Uses `SingleNestedNode.check_node()`
        '''
        self.nodes.update(dict.fromkeys(names, None))
        for n in names:
            self.nodes[n] = SingleNestedNode.check_node(self, n)
            if self.nodes[n] is None: return
    def compile(self) -> None:
        '''Attempts to compile this node against the contained nodes'''
        self.failure = None
        if self.check_unbound(): return
        self.check_nodes(*self.nodes.keys())
