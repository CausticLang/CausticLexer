#!/bin/python3

'''
    Provides functions for saving and loading nodes
        for caching or transportation
'''

#> Imports
import io
import pickle
import typing
import pickletools

from . import nodes
from .util import bind_nodes
#</Imports

#> Header >/
__all__ = ('NodePickler', 'NodeUnpickler',
           'serialize', 'serialize_to',
           'deserialize', 'deserialize_from')

# Picklers
class NodePickler(pickle.Pickler):
    '''Pickles nodes, using `.persistent_id()` for node class names'''
    __slots__ = ()

    def persistent_id(self, obj: typing.Any) -> int | None:
        if isinstance(obj, type) and issubclass(obj, nodes.Node):
            try:
                return nodes.__all__.index(obj.__name__)
            except ValueError:
                return None
        return None
class NodeUnpickler(pickle.Unpickler):
    '''Unpickles nodes from `NodePickler`, using `.persistent_load()` for node class names'''
    __slots__ = ()

    def persistent_load(self, pid: int) -> type[nodes.Node]:
        if not isinstance(pid, int):
            raise pickle.UnpicklingError(f'Persistent node ID should be an int')
        try: return getattr(nodes, nodes.__all__[pid])
        except IndexError:
            raise pickle.UnpicklingError(f'Persistent node ID is invalid')

# Functions
## Serialization
def serialize(nodes: dict[bytes, nodes.Node], *, optimize: bool = True) -> bytes:
    '''
        Serializes `nodes`
        Note: all nodes are unbound; if they are used
            elsewhere this will cause side-effects
    '''
    with io.BytesIO() as bio:
        serialize_to(nodes, bio)
        data = bio.getvalue()
    if optimize: data = pickletools.optimize(data)
    return data
def serialize_to(nodes: dict[bytes, nodes.Node], to: typing.BinaryIO) -> None:
    '''
        Serializes `nodes` into a file-like object
        Note: all nodes are unbound; if they are used
            elsewhere this will cause side-effects
    '''
    p = NodePickler(to)
    for n in nodes.values(): n.unbind()
    p.dump(tuple(nodes.items()))
## Deserialization
def deserialize(data: bytes, *, bind: bool = True) -> dict[bytes, nodes.Node]:
    '''Deserializes nodes from `data`'''
    with io.BytesIO(data) as bio:
        return deserialize_from(bio, bind=bind)
def deserialize_from(from_: typing.BinaryIO, *, bind: bool = True) -> dict[bytes, nodes.Node]:
    '''Deserializes nodes from a file-like object'''
    nup = NodeUnpickler(from_)
    nodes = dict(nup.load())
    if bind: bind_nodes(nodes)
    return nodes
