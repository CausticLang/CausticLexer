#!/bin/python3

'''Provides the `Compiler` class'''

#> Imports
import re
import codecs
import typing
import buffer_matcher
from pathlib import Path
from functools import singledispatchmethod
from collections import abc as cabc

from . import nodes
from . import util
#</Imports

#> Header >/
__all__ = ('Compiler',)

class Compiler:
    '''Compiles grammars'''
    __slots__ = ('grammar', 'base_path')

    grammar: dict[bytes, nodes.Node]
    base_path: Path

    def __init__(self, grammar: dict[bytes, nodes.Node],
                 base_path: Path = Path(__file__).parent):
        self.grammar = grammar
        self.base_path = base_path

    # Compiling
    @singledispatchmethod
    def compile(self, src: Path | typing.BinaryIO | bytes | buffer_matcher.SimpleBufferMatcher | dict, *,
                source: Path | str | None = None, bind: bool = True) -> dict[bytes, nodes.Node]:
        '''Compiles grammars from various sources'''
        raise TypeError(f'Cannot compile from type {type(src).__qualname__}')

    ## Intermediate source types
    @compile.register
    def compile_path(self, path: Path, *, source: Path | str | None = None, **kwargs) -> dict[bytes, nodes.Node]:
        '''
            Compiles from a path
            See `.compile()` or `.compile_buffermatcher()` for `kwargs`
        '''
        return self.compile_bytes(path.read_bytes(), source=path if source is None else source, **kwargs)
    @compile.register
    def compile_file(self, file: typing.BinaryIO, *, source: Path | str | None = None, **kwargs) -> dict[bytes, nodes.Node]:
        '''
            Compiles from a file
            See `.compile()` or `.compile_buffermatcher()` for `kwargs`
        '''
        return self.compile_bytes(file.read(), source=file.name if source is None else source, **kwargs)
    @compile.register
    def compile_bytes(self, data: bytes, *, source: Path | str | None = None, **kwargs) -> dict[bytes, nodes.Node]:
        '''
            Compiles from bytes
            See `.compile()` or `.compile_buffermatcher()` for `kwargs`
        '''
        return self.compile_buffermatcher(buffer_matcher.DynamicBufferMatcher(data),
                                          source='<bytes>' if source is None else source, **kwargs)
    @compile.register
    def compile_buffermatcher(self, bm: buffer_matcher.SimpleBufferMatcher,
                              source: Path | str | None = None, bind: bool = True,
                              precompile_only: bool = False) -> dict[bytes, nodes.Node]:
        '''Compiles a grammar (dict of names and nodes) from a buffer matcher'''
        if source is None: source = '<buffermatcher>'
        try: pre = self.pre_process(bm, source=source, bind=bind)
        except Exception as e:
            e.add_note(f'Whilst pre-processing grammar from: {source}')
            raise e
        if precompile_only: return pre
        try: return self.post_process_compile(pre, bind=bind)
        except Exception as e:
            e.add_note(f'Whilst post-process compiling grammar from: {source}')
            raise e

    ## Pre-process
    def pre_process(self, bm: buffer_matcher.SimpleBufferMatcher,
                    source: Path | str | None = None) -> dict[bytes, dict]:
        '''
            Reads a buffer matcher and parses it into a format suitable for compilation
            Also handles pragmas
        '''
        working = {}
        while True:
            # Discard junk characters and check for EOF
            while bm.match(util.WHITESPACE_PATT) or self.grammar[b'COMMENT'](bm):
                pass # ignore whitespace and comments
            if not bm.peek(1): break # EOF
            # Handle pragmas
            if p := self.grammar[b'PRAGMA'](bm):
                try: self.handle_pragma(p['type'], p['args'], working=working, bm=bm, source=source)
                except Exception as e:
                    e.add_note(f'In pragma at {bm.pos} ({bm.lno}:{bm.cno})')
                    raise e
                continue
            # Parse statements
            stmt = self.grammar[b'STATEMENT'](bm, stealer=True)
            working[stmt['name']] = stmt['expr']
        return working
    ### Pragma
    def handle_pragma(self, type_: bytes, args: bytes, *, working: dict[bytes, dict],
                      bm: buffer_matcher.SimpleBufferMatcher, source: Path | str | None = None) -> None:
        '''Handles a pragma statement during compilation'''
        match type_:
            case b'include':
                if not args:
                    raise SyntaxError('Include pragma requires args')
                f = Path(args.decode())
                if f.is_absolute():
                    working.update(self.compile_path(f, bind=False, precompile_only=True))
                    return
                if isinstance(source, Path) and (nf := (source.parent / f)).is_file(): pass
                elif (nf := (Path.cwd() / f)).is_file(): pass
                elif (nf := (self.base_path / f)).is_file(): pass
                else: raise FileNotFoundError(f'Cannot resolve relative file from include: {f}')
                working.update(self.compile_path(nf, bind=False, precompile_only=True))
            case _:
                raise TypeError(f'Unknown pragma type {type_!r}')

    ## Compile
    def post_process_compile(working: dict[bytes, dict], *, bind: bool = True) -> dict[bytes, nodes.Node]:
        '''Compiles pre-processed grammar into nodes'''
        for k,v in working.items():
            print(k, v)
