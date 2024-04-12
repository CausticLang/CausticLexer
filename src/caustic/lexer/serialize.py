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
#</Imports

#> Header >/
__all__ = ('NodePickler',
           'serialize', 'serialize_to')

class NodePickler(pickle.Pickler):
    '''Pickles nodes, using `.persistent_id()` for class names'''
    __slots__ = ()

    def persistent_id(self, obj: typing.Any) -> int | None:
        if isinstance(obj, type) and issubclass(obj, nodes.Node):
            try:
                return nodes.__all__.index(obj.__name__)
            except ValueError:
                return None
        return None

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
        Serializes `nodes` into a stream
        Note: all nodes are unbound; if they are used
            elsewhere this will cause side-effects
    '''
    p = NodePickler(to)
    for n in nodes.values(): n.unbind()
    p.dump(tuple(nodes.items()))
