#!/bin/python3

#> Imports
import io
import re
import typing
from dataclasses import dataclass
from collections.abc import Callable

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
    __slots__ = ('grammer', 'buffer', 'source', 'lno', 'cno', 'token_finders', 'last', 'indent_size')

    MARK_TOKSUCC = object()

    grammer: Grammer
    buffer: typing.TextIO
    source: str | None
    lno: int; cno: int

    token_finders: tuple[Callable[[str, bool], None | tokens.Token | object], ...]
    last: None | tokens.Token
    indent_size: None | int

    def __init__(self, grammer: Grammer):
        self.grammer = grammer
        self.buffer = io.StringIO()
        self.source = None
        self.lno = self.cno = 0
        self.token_finders = (
            self.tok_eof, self.tok_eol,
            self.tok_pragma,
            self.tok_comment_single, self.tok_comment_block,
            self.tok_block_start, self.tok_block_end,
                self.tok_indent_mark, self.tok_indent,
        )
        self.last = self.indent_size = None
    def __del__(self):
        self.buffer.close()

    def write(self, data: str) -> int:
        '''Writes data to the end of the buffer and restores the stream position (on success)'''
        start = self.buffer.tell()
        self.buffer.seek(0, io.SEEK_END)
        written = self.buffer.write(data)
        self.buffer.seek(start)
        return written

    def _b_read_until(self, until: str, *, allow_eof: bool = False) -> str:
        start = self.buffer.tell()
        try: index = self.buffer.read().index('\n')
        except ValueError:
            if not allow_eof:
                raise ParseError(f'{until!r} expected (reached EOF)', source=self.source, lno=self.lno, cno=self.cno)
            index = -1
        self.buffer.seek(start)
        return self._b_read(index)
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
        self.cno = len(text.rsplit('\n')[-1])
        return text
    def _b_backup(self, count: int) -> int:
        # WARNING: .lno and .cno will be desynced if newlines are backed over!
        # returns the original buffer position
        loc = self.buffer.tell()
        self.buffer.seek(loc - count)
        self.cno -= count
        return loc
    def _b_lookahead(self, count: int) -> str:
        curr = self.buffer.tell()
        text = self.buffer.read(count)
        self.buffer.seek(curr)
        return text
    def _b_chk_for(self, val: str, consume_success: bool) -> bool:
        curr = self.buffer.tell()
        success = self.buffer.read(len(val)) == val
        if (not success) or (not consume_success):
            self.buffer.seek(curr)
        return success

    def tokenize(self) -> typing.Generator[tokens.Token, None, None]:
        '''Yields all tokens until an exception occurs or EOF is reached'''
        while True:
            tok = self.tokenize_pass_once()
            if tok is None: continue
            yield tok
            if isinstance(tok, tokens.EOF): return
    def tokenize_pass_once(self) -> tokens.Token | tuple[tokens.Token] | None:
        '''Moves over one read, returning a `Token` or `None`'''
        c = self._b_read(1)
        nl = isinstance(self.last, tokens.NewlineEOL)
        for finder in self.token_finders:
            res = finder(c, nl)
            if callable(res): # `Token` class or `Token.part` method
                res = res(src=self.source, lno=self.lno, cno=self.cno)
            if isinstance(res, tokens.Token):
                self.last = res
                return res
            if res is self.MARK_TOKSUCC: return None
        raise ParseError(f'Unexpected character: {c!r}', source=self.source, lno=self.lno, cno=self.cno)

    # Indentation manager
    def consume_indentation(self) -> int:
        '''Consumes indentation'''
        count = 0
        while self._b_chk_for(' '*self.indent_size, True): count += 1
        if self._b_chk_for(' ', True):
            raise ParseError(f'Extraneous leading space in indented block', source=self.source, lno=self.lno, cno=self.cno)
        return count

    # Token finders
    def _tok_start_helper(self, c: str, target: str) -> bool:
        '''A helper function that checks for (and consumes) the `target` string in the buffer'''
        return target.startswith(c) and self._b_chk_for(target[1:], True)

    def tok_eof(self, c: str, nl: bool) -> tokens.Token | None:
        if not c: return tokens.EOF
        return None
    def tok_eol(self, c: str, nl: bool) -> tokens.Token | None:
        if self._tok_start_helper(c, self.grammer.line.eol): return tokens.EOL
        if self.grammer.line.newline.enable:
            if c == '\n': return tokens.NewlineEOL
            if c == self.grammer.line.newline.cont:
                if self._b_chk_for('\n', True): return None
                raise ParseError('Unexpected line continuation character', source=self.source, lno=self.lno, cno=self.cno)
        return None

    def tok_pragma(self, c: str, nl: bool) -> object | None:
        if not self._tok_start_helper(c, self.grammer.pragma.start): return None
        pnt,parg = (self._b_read_until(self.grammer.pragma.stop)
                    .split(self.grammer.pragma.vsep, 1))
        ptype,*pname = pnt.split(self.grammer.pragma.tsep)
        pragma.pragma(ptype, pname, parg, tokenizer=self)
        return self.MARK_TOKSUCC

    def tok_comment_single(self, c: str, nl: bool) -> tokens.Token | None:
        if not self._tok_start_helper(c, self.grammer.comment.single): return None
        return tokens.Comment.part(self._b_read_until('\n', allow_eof=True))
    def tok_comment_block(self, c: str, nl: bool) -> tokens.Token | None:
        if not self._tok_start_helper(c, self.grammer.comment.block[0]): return None
        return tokens.Comment.part(self._b_read_until(self.grammer.comment.block[1]))

    ## Blocks
    def tok_block_start(self, c: str, nl: bool) -> tokens.Token | None:
        if self.grammer.block.delim and self._tok_start_helper(c, self.grammer.block.delim[0]):
            return tokens.Block.Start
        return None
    def tok_block_end(self, c: str, nl: bool) -> tokens.Token | None:
        if self.grammer.block.delim and self._tok_start_helper(c, self.grammer.block.delim[1]):
            return tokens.Block.End
        return None
    ### Indentation
    def tok_indent_mark(self, c: str, nl: bool) -> tokens.Token | None:
        if self.grammer.block.indent and nl and self._tok_start_helper(c, self.grammer.block.indent):
            return tokens.Block.IndentMark
        return None
    def tok_indent(self, c: str, nl: bool) -> tokens.Token | None:
        if not (self.grammer.block.indent and nl and (c == ' ')): return None
        loc = self._b_backup(1)
        if self.indent_size is None:
            self.indent_size = 1
            self.indent_size = self.consume_indentation()
            lvl = 1
        else: lvl = self.consume_indentation()
        if not lvl: self.indent_size = None
        if loc-1 == self.buffer.tell():
            self._b_read(1)
        return tokens.Block.Indent.part(lvl)
