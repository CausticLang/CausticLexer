#!/bin/python3

'''Handles pragma statements'''

#> Imports
import sys
from collections import abc as cabc

from . import tokenizer
#</Imports

#> Header >/
__all__ = ('PragmaError', 'pragma', 'types',
           'grammer', 'print_')

class PragmaError(Exception):
    '''Errors that occur that are directly related to pragmas'''
    __slots__ = ()

def pragma(type_: str, name: cabc.Sequence[str], arg: str, *, tokenizer: 'tokenizer.Tokenizer') -> None:
    if (meth := types.get(type_, None)) is not None:
        return meth(name, arg, tokenizer)
    raise PragmaError(f'Unknown pragma type: {type_!r}')

# Pragma types
def grammer(name: cabc.Sequence[str], arg: str, tokenizer: 'tokenizer.Tokenizer') -> None:
    tokenizer.grammer.fn_chone(f'{".".join(name)}:{arg}', source=f'<pragma@{tokenizer.source or "<unknown>"}'
                               f' l{"?" if tokenizer.lno < 0 else tokenizer.lno}'
                               f' c{"?" if tokenizer.lno < 0 else tokenizer.cno}')

def print_(name: cabc.Sequence[str], arg: str, tokenizer: 'tokenizer.Tokenizer') -> None:
    if name:
        raise PragmaError('Unexpected "name" value in print pragma')
    print(arg, file=sys.stderr)

types = {
    'grammer': grammer,
    'print': print_,
}
