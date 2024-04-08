#!/bin/python3

'''Provides functions for creating nodes from a structured file'''

#> Imports
import io
import os
import copy
import typing
import tomllib
from pathlib import Path
from contextlib import nullcontext
from collections import abc as cabc

from .. import nodes
#</Imports

#> Header >/
__all__ = ('NODE_KEYS', 'load_dict', 'load')

NODE_KEYS = {}
for grpn in ('flat', 'nested', 'meta'):
    grp = getattr(nodes, grpn)
    NODE_KEYS.update((f'{grpn}.{noden.lower().removesuffix("node")}', getattr(grp, noden))
                     for noden in grp.__all__)

def load_dict(src: cabc.Mapping[str, typing.Any], *, node_keys: cabc.Mapping[str, nodes.GrammarNode] = NODE_KEYS) -> cabc.Generator[tuple[str, nodes.GrammarNode], None, None]:
    '''Creates nodes from a structured dictionary'''
    src = copy.deepcopy(src)
    for name,config in src.items():
        if (ntypen := config.pop('type', None)) is None:
            raise TypeError(f'Cannot create node {name!r}, as its configuration is missing a type')
        if (ntype := node_keys.get(ntypen, None)) is None:
            raise TypeError(f'Unknown node type for node {name!r}: {ntypen!r}')
        try: yield name, ntype(name, **config)
        except Exception as e:
            e.add_note(f'Occured whilst attempting to create node {name!r} from creation')
            raise e

def load(*files: str | os.PathLike | typing.BinaryIO, **kwargs) -> dict[str, nodes.GrammarNode]:
    '''Loads each file/path in `files` as TOML and then passes the result to `load_dict()`'''
    nodes = {}
    for f in files:
        with (nullcontext(f) if isinstance(f, io.BufferedReader) else open(f, 'rb')) as f:
            nodes.update(tomllib.load(f))
    return load_dict(nodes)
