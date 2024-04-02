#!/bin/python3

#> Imports
import typing
#</Imports

#> Header >/
__all__ = ('Token',
           'Comment')

class Token:
    '''Base token type'''
    __slots__ = ('src', 'lno', 'cno')

    def __init__(self, *, src: str | None, lno: int, cno: int):
        self.src = src
        self.lno = lno
        self.cno = cno

# Bases
class _BaseValToken(Token):
    '''Base token type that takes a single value'''
    __slots__ = ('val',)

    def __init__(self, val: typing.Any, **kwargs):
        self.vals = val
        super().__init__(**kwargs)
class _BaseValToken(Token):
    '''Base token type that takes multiple values'''
    __slots__ = ('vals',)

    def __init__(self, *vals: typing.Any, **kwargs):
        self.vals = vals
        super().__init__(**kwargs)

# Tokens
class Comment(BaseValToken):
    '''Denotes a single or multi-line comment'''
    __slots__ = ()
