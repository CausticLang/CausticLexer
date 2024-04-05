#!/bin/python3

#> Header >/
__all__ = ('NodeException',
           'NodeMissingError', 'BaseNodeMissingError', 'CompiledNodeMissingError',
           'NodeExistsError',
           'NodeNotReadyException')

class NodeException(Exception):
    '''Base exception for nodes'''
    __slots__ = ()
class _NamedNodeException(NodeException):
    # adds a "nodename" parameter
    __slots__ = ('nodename',)
    def __init__(self, nodename: str, *args, **kwargs):
        self.nodename = nodename
        super().__init__(*args, **kwargs)

class NodeMissingError(_NamedNodeException, KeyError):
    '''For when a needed node is missing'''
    __slots__ = ()
class BaseNodeMissingError(NodeMissingError):
    '''For when a needed node base is missing'''
    __slots__ = ()
class CompiledNodeMissingError(NodeMissingError):
    '''For when a needed (partially-)compiled node is missing'''
    __slots__ = ()

class NodeExistsError(_NamedNodeException):
    '''For when a node exists when it shouldn't'''
    __slots__ = ()

class NodeNotReadyException(_NamedNodeException):
    '''For when a node isn't ready'''
    __slots__ = ()
