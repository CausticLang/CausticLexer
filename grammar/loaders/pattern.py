#!/bin/python3

'''
    Provides the `PatternLoader` mixin class for loading patterns
        into a `PatternComposer` from a TOML file
'''

#> Imports
import io
import os
import typing
import tomllib
from contextlib import nullcontext
from regex_compose import PatternComposer
from collections import abc as cabc
#</Imports

#> Header >/
__all__ = ('PatternLoader',)

class PatternLoader(PatternComposer):
    '''A subclass of `PatternComposer` that allows loading of patterns from TOML files'''
    __slots__ = ()

    def __init__(self):
        super().__init__(bytes_mode=True)

    @classmethod
    def _convert(cls, target: dict[str, str | dict], *, _name: tuple[str, ...] = ()) -> cabc.Iterable[tuple[str, bytes]]:
        for k,v in target.items():
            if isinstance(v, dict):
                yield from cls._convert(v, _name=(_name+(k,)))
            else: yield ('.'.join(_name+(k,)), v.encode())

    def load(self, *files: str | os.PathLike | typing.BinaryIO) -> None:
        '''Loads each file in `files` (can be paths or binary file objects) as TOML'''
        patts = {}
        for f in files:
            with (nullcontext(f) if isinstance(f, io.BufferedReader) else open(f, 'rb')) as f:
                patts.update(self._convert(tomllib.load(f)))
        self.multiadd(patts, replace=True)
