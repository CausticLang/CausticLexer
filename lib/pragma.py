#!/bin/python3

'''Handles pragma statements'''

#> Imports
import sys
from collections import abc as cabc

from . import tokenizer
#</Imports

#> Header >/
__all__ = ('pragma', 'PragmaError',
           'grammer', 'print_')

class PragmaError(Exception):
    '''Errors that occur that are directly related to pragmas'''
    __slots__ = ()

def pragma(type_: str, name: cabc.Sequence[str], arg: str, *, tokenizer: 'tokenizer.Tokenizer') -> None:
    if type_ == 'grammer':
        return grammer(name, arg, tokenizer)
    if type_ == 'print':
        return print_(name, arg, tokenizer)
    raise PragmaError(f'Unknown pragma type: {type_!r}')

def grammer(name: cabc.Sequence[str], arg: str, *, tokenizer: 'tokenizer.Tokenizer') -> None:
    tokenizer.grammer.chone(name, source=f'<pragma@{tokenizer.source or "<unknown>"}'
                            f' l{"?" if tokenizer.lno < 0 else tokenizer.lno}'
                            f' c{"?" if tokenizer.lno < 0 else tokenizer.cno}')

def print_(name: cabc.Sequence[str], arg: str, *, tokenizer: 'tokenizer.Tokenizer') -> None:
    if name:
        raise PragmaError('Unexpected "name" value in print pragma')
    print(arg, file=sys.stderr)
