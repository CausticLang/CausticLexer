#!/bin/python3

#> Imports
import io
import re
import typing
from dataclasses import dataclass

from . import tokens # re-exposed

from .grammer_parser import Grammer
from .grammer_parser import exceptions as gexc

from . import pragma
#</Imports

#> Header >/
__all__ = ('tokens', 'Tokenizer', 'ParseError', 'EOFParseError')

class ParseError(Exception):
    '''When errors occur whilst tokenizing Caustic source'''
    __slots__ = ('source', 'lno', 'cno')

    source: str | None
    lno: int; cno: int

    def __init__(self, *args, source: str | None, lno: int, cno: int, **kwargs):
        self.source = source
        self.lno = lno
        self.cno = cno
        super().__init__(*args, **kwargs)
class EOFParseError(ParseError):
    '''When errors occur whilst tokenizer Caustic source due to reaching EOF'''
    __slots__ = ()

class Tokenizer:
    '''
        Tokenizes Caustic source code into tokens
        Note: holds state
    '''
    __slots__ = ('grammer', 'buffer', 'source', 'lno', 'cno')

    grammer: Grammer
    buffer: typing.TextIO
    source: str | None
    lno: int; cno: int

    def __init__(self, grammer: Grammer):
        self.grammer = grammer
        self.buffer = io.StringIO()
        self.source = None
        self.lno = self.cno = 0
    def __del__(self):
        self.buffer.close()

    def _b_read_until(self, until: str) -> str:
        try: text = ''.join(iter(lambda: self.buffer.read(1), until))
        except StopIteration:
            raise ParseError(f'{until!r} expected (reached EOF)', source=self.source, lno=self.lno, cno=self.cno)
        self.lno += text.count('\n')
        if until == '\n': self.lno += 1
        self.cno = len(text.rsplit('\n')[1])
        return text
    def _b_read_regex(self, patt: re.Pattern) -> str:
        start = self.buffer.tell()
        text = self.buffer.read()
        mat = patt.match(text)
        if mat is None:
            raise ParseError(f'Expected pattern: {patt}', source=self.source, lno=self.lno, cno=self.cno)
        self.buffer.seek(start + mat.end())
        self._b_read(mat.end())

    def _b_read(self, count: int) -> str:
        text = self.buffer.read(count)
        self.lno += text.count('\n')
        self.cno = len(text.rsplit('\n')[1])
        return text

    def tokenize_pass_once(self) -> typing.Generator[Token, None, None]:
        '''Moves over one read, yielding as many tokens as that read yields (including no tokens)'''
        match self._b_read(1):
            case '': return # EOF
            case self.grammer.pragma.start:
                val = self.pragma()
            case _ as c:
                raise ParseError(f'Unexpected character: {c!r}', source=self.source, lno=self.lno, cno=self.cno)
        if val is None: return
        if isinstance(val, Token): yield val
        else: yield from val

    # Token yielders
    def pragma(self) -> None:
        pnt,parg = (self._b_read_until(self.grammer.pragma.stop)
                    .split(self.grammer.pragma.vsep, 1))
        ptype,*pname = pnt.split(self.grammer.pragma.tsep)
        pragma.pragma(ptype, pname, parg, tokenizer=self)

    def comment(self) -> None: pass
