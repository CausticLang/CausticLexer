#!/bin/python3

'''Provides functions for compiling Caustic grammar'''

#> Imports
import re
import buffer_matcher
from enum import Enum
from collections import abc as cabc
#</Imports

#> Header >/
__all__ = ('GrammarTypes', 'Markers', 'RE_FLAGS', 'PATTERNS',
           'consume_whitespace',
           'compile', 'compile_inner')

type GrammarTypes = re.Pattern | str | Markers

Markers = Enum('Markers', ('UNION', 'STEALER', 'TARGET', 'PARENS',
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

def consume_whitespace(data: buffer_matcher.AbstractBufferMatcher):
    '''Helper function to consume whitespace characters'''
    while (c := data.peek()) and (c in b' \n\r\t'):
        data.step()

def compile(data: buffer_matcher.AbstractBufferMatcher) -> cabc.Generator[tuple[bytes, tuple[GrammarTypes | tuple, ...]], None, None]:
    '''Compiles a Caustic grammar file'''
    consume_whitespace(data)
    while (c := data.peek()):
        if (((mt := data(PATTERNS['terminal'].match)) is not None)
                or ((mnt := data(PATTERNS['nonterminal'].match)) is not None)):
            consume_whitespace(data)
            if (c := data.step()) != b'=':
                raise ValueError(f'Unexpected character {bytes(c)!r} (expected {b"="!r}) at pos {data.pos} (line {data.lno} column {data.cno})')
            yield ((mt or mnt).group(1), tuple(compile_inner(data, terminal=(mt is not None), finalizer=b';')))
        else:
            raise ValueError(f'Unexpected character {bytes(c)!r} at pos {data.pos} (line {data.lno} column {data.cno})')
        consume_whitespace(data)

def compile_inner(data: buffer_matcher.AbstractBufferMatcher, *, terminal: bool, finalizer: bytes) -> cabc.Generator[GrammarTypes | tuple, None, None]:
    '''Helper function to compile the inside of a terminal or nonterminal'''
    consume_whitespace(data)
    while (c := data.peek()):
        consume_whitespace(data)
        if not (c := data.peek()): break
        if m := data(PATTERNS['regex'].match):
            flags = re.NOFLAG
            for f in m.group('f'):
                if (flag := RE_FLAGS.get(f, None)) is not None:
                    flags |= flag
                    continue
                raise ValueError(f'Unknown flag {f!r} ({bytes((f,))!r}) in {m.group(0)}')
            yield re.compile(m.group('p'), flags)
            continue
        if m := data(PATTERNS['string'].match):
            yield m.group(1)
            continue
        if not terminal:
            if (((mt := data(PATTERNS['terminal'].match)) is not None)
                    or ((mnt := data(PATTERNS['nonterminal'].match)) is not None)):
                yield Markers.TERMINAL if mt is not None else Markers.NONTERMINAL
                yield (mt or mnt).group(1)
            continue
        data.step()
        if c == finalizer: return
        if c == b'!': yield Markers.STEALER
        elif c == b'<':
            yield Markers.TARGET
            yield tuple(compile_inner(data, terminal=terminal, finalizer=b'>'))
        elif c == b'(':
            yield Markers.PARENS
            yield tuple(compile_inner(data, terminal=terminal, finalizer=b')'))
        elif c == b'|':
            yield Markers.UNION
        else: raise ValueError(f'Unexpected character {bytes(c)!r} at pos {data.pos} (line {data.lno} column {data.cno})')
    raise EOFError(f'Encountered EOF without reaching finalizing character {finalizer}')
