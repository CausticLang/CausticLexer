#!/bin/python3

#> Imports
import re
import buffer_matcher
from enum import Enum
from functools import partial
from collections import abc as cabc
#</Imports

#> Header >/
__all__ = ('compile',)

class Grammar:
    '''...'''
    __slots__ = ()

    Special = Enum('Special', ('UNION', 'RANGE', 'STEALER',
                               'TARGET', 'PARENS',
                               'TERMINAL', 'NONTERMINAL'))

    RE_FLAGS = {
        b'i'[0]: re.IGNORECASE,
        b'm'[0]: re.MULTILINE,
        b's'[0]: re.DOTALL,
    }

    PATTERNS = {
        'terminal': re.compile(br'([A-Z]+)'),
        'nonterminal': re.compile(br'([a-z]+)'),
        'regex': re.compile(br'/(?P<p>(?:[^/\\]|(?:\\.))*)/(?P<f>[ims]*)', re.DOTALL),
        'string': re.compile(br'''((?:"(?:[^\\"]|(?:\\.))*")|(?:'(?:[^\\']|(?:\\.))*'))''', re.DOTALL),
    }

    @staticmethod
    def _consume_whitespace(data: buffer_matcher.AbstractBufferMatcher):
        while (c := data.peek()) and (c in b' \n\r\t'):
            data.step()
    @classmethod
    def compile(cls, data: buffer_matcher.AbstractBufferMatcher) -> cabc.Generator[tuple[str, tuple[re.Pattern | str | Special | tuple, ...]], None, None]:
        cls._consume_whitespace(data)
        while (c := data.peek()):
            if (((mt := data(cls.PATTERNS['terminal'].match)) is not None)
                    or ((mnt := data(cls.PATTERNS['nonterminal'].match)) is not None)):
                cls._consume_whitespace(data)
                if (c := data.step()) != b'=':
                    raise ValueError(f'Unexpected character {bytes(c)!r} (expected {b"="!r}) at pos {data.pos} (line {data.lno} column {data.cno})')
                yield ((mt or mnt).group(1), tuple(cls.compile_inner(data, terminal=(mt is not None), finalizer=b';')))
            else:
                raise ValueError(f'Unexpected character {bytes(c)!r} at pos {data.pos} (line {data.lno} column {data.cno})')
            cls._consume_whitespace(data)
    @classmethod
    def compile_inner(cls, data: buffer_matcher.AbstractBufferMatcher, *, terminal: bool, finalizer: bytes) -> cabc.Generator[re.Pattern | str | Special | tuple, None, None]:
        cls._consume_whitespace(data)
        while (c := data.peek()):
            cls._consume_whitespace(data)
            if not (c := data.peek()): break
            if m := data(cls.PATTERNS['regex'].match):
                flags = re.NOFLAG
                for f in m.group('f'):
                    if (flag := cls.RE_FLAGS.get(f, None)) is not None:
                        flags |= flag
                        continue
                    raise ValueError(f'Unknown flag {f!r} ({bytes((f,))!r}) in {m.group(0)}')
                yield re.compile(m.group('p'), flags)
                continue
            if m := data(cls.PATTERNS['string'].match):
                yield m.group(1)
                continue
            if not terminal:
                if (((mt := data(cls.PATTERNS['terminal'].match)) is not None)
                        or ((mnt := data(cls.PATTERNS['nonterminal'].match)) is not None)):
                    yield cls.Special.TERMINAL if mt is not None else cls.Special.NONTERMINAL
                    yield (mt or mnt).group(1)
                continue
            data.step()
            if c == finalizer: return
            if c == b'!': yield cls.Special.STEALER
            elif c == b'<':
                yield cls.Special.TARGET
                yield tuple(cls.compile_inner(data, terminal=terminal, finalizer=b'>'))
            elif c == b'(':
                yield cls.Special.PARENS
                yield tuple(cls.compile_inner(data, terminal=terminal, finalizer=b')'))
            elif c == b'|':
                yield cls.Special.UNION
            else: raise ValueError(f'Unexpected character {bytes(c)!r} at pos {data.pos} (line {data.lno} column {data.cno})')
        raise EOFError(f'Encountered EOF without reaching finalizing character {finalizer}')
