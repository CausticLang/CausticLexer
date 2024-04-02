#!/bin/python3

#> Imports
import typing
from types import SimpleNamespace
from collections import abc as cabc
#</Imports

#> Header >/
__all__ = ('Token',
           'EOF', 'EOL', 'NewlineEOL', 'Comment', 'Block')

class Token:
    '''Base token type'''
    __slots__ = ('src', 'lno', 'cno')

    def __init__(self, *, src: str | None, lno: int, cno: int):
        self.src = src
        self.lno = lno
        self.cno = cno

    @classmethod
    def part(cls, *oargs, **okwargs) -> cabc.Callable[[...], typing.Self]:
        def tokenbuilder(*iargs, **ikwargs) -> Token:
            return cls(*oargs, *iargs, **okwargs, **ikwargs)
        return tokenbuilder

# Bases
class _BaseValToken(Token):
    '''Base token type that takes a single value'''
    __slots__ = ('val',)

    def __init__(self, val: typing.Any, **kwargs):
        self.val = val
        super().__init__(**kwargs)
class _BaseValsToken(Token):
    '''Base token type that takes multiple values'''
    __slots__ = ('vals',)

    def __init__(self, *vals: typing.Any, **kwargs):
        self.vals = vals
        super().__init__(**kwargs)

# Tokens
class EOF(Token):
    '''Denotes the end of a file'''
    __slots__ = ()
class EOL(Token):
    '''Denotes the end of a line (A.E., ";" (and "\\n" with line.newline.enable))'''
    __slots__ = ()
class NewlineEOL(EOL):
    '''Denotes the end of line, specifically by a newline'''
    __slots__ = ()

class Comment(_BaseValToken):
    '''Denotes a single or multi-line comment'''
    __slots__ = ()

## Blocks
class BlockStart(Token):
    '''Denotes the start of a block'''
    __slots__ = ()
class BlockEnd(Token):
    '''Denotes the end of a block'''
    __slots__ = ()
Block = SimpleNamespace(Start=BlockStart,
                        End=BlockEnd)
del BlockStart, BlockEnd
### Indentation
class IndentMark(Token):
    '''Denotes the start of an indent-style block'''
    __slots__ = ()
class Indent(_BaseValToken):
    '''Denotes sensitive indentation'''
    __slots__ = ()
Block.IndentMark = IndentMark
Block.Indent = Indent
del IndentMark, Indent
