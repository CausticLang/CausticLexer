#!/bin/python3

#> Imports
import re
import codecs
import struct
from types import SimpleNamespace
from buffer_matcher import SimpleBufferMatcher
from collections import abc as cabc

import nodes
#</Imports

#> Header >/
__all__ = ()

PATTERNS = SimpleNamespace(
    whitespace = re.compile(rb'\s+', re.MULTILINE),
    comment = re.compile(rb'#.*$', re.MULTILINE),
    discard = None,
    statement = re.compile(rb'^([\w]+)\s*=\s*', re.MULTILINE),
    named = re.compile(rb'([\w]*):'),
    string = re.compile(rb'"((?:[^\\"]|(?:\\.))*)"'),
    regex = re.compile(rb'(?P<g>\d)?/(?P<p>(?:[^\\/]|(?:\\.))+)/(?P<f>[ims]*)'),
    context = re.compile(rb'(\w*)'),
)
PATTERNS.discard = re.compile(b'((' + PATTERNS.whitespace.pattern + b')|(' + PATTERNS.comment.pattern + b'))+', re.MULTILINE)

CHARS = SimpleNamespace(
    statement_stop = b';',
    group_start = b'(', group_stop = b')',
    group_nospace_start = b'{', group_nospace_stop = b'}',
    union_start = b'[', union_stop = b']',
    context_start = b'<', context_stop = b'>',
    stealer = b'!',
)

def compile(bm: SimpleBufferMatcher) -> cabc.Generator[tuple[str, nodes.Node], None, None]:
    while True:
        bm.match(PATTERNS.discard)
        if not bm.peek(1): return # EOF
        if (m := bm.match(PATTERNS.statement)) is not None:
            yield (m.group(1), nodes.NodeGroup(*tuple(compile_expression(bm))))
        else:
            raise ValueError(f'Expected statement at {bm.pos} ({bm.lno+1}:{bm.cno})')

RE_FLAGS = {
    b'i': re.IGNORECASE,
    b'm': re.MULTILINE,
    b's': re.DOTALL,
}

def compile_expression(bm: SimpleBufferMatcher, *, _stop: bytes = CHARS.statement_stop,
                       _in_group: bool = False) -> cabc.Generator[nodes.Node, None, None]:
    while True:
        bm.match(PATTERNS.discard)
        # pre-nodes
        if (m := bm.match(PATTERNS.named)) is not None:
            name = m.group(1).decode()
            bm.match(PATTERNS.discard)
        else: name = None
        # check for EOF
        if not bm.peek():
            if name is None:
                raise EOFError(f'Reached end of file before stop-mark {_stop!r}')
            raise EOFError('Reach end of file, but expected node after name-pattern')
        # nodes
        if (m := bm.match(PATTERNS.string)) is not None:
            node = nodes.StringNode(codecs.escape_decode(m.group(1))[0])
        elif (m := bm.match(PATTERNS.regex)) is not None:
            flags = re.NOFLAG
            for f in struct.unpack(f'{len(m.group("f"))}c', m.group('f')):
                flag = RE_FLAGS.get(f, None)
                if flag is None:
                    raise ValueError(f'Unknown regular expression flag {f!r} at {bm.pos} ({bm.lno+1}:{bm.cno})')
                flags |= flag
            node = nodes.PatternNode(re.compile(m.group('p'), flags), None if m.group('g') is None else int(m.group('g')))
        else:
            match bm.read(1):
                case CHARS.stealer:
                    if not _in_group:
                        raise SyntaxError(f'Cannot add stealer node outside of group (@{bm.pos} ({bm.lno+1}:{bm.cno}))')
                    if name is not None:
                        raise SyntaxError(f'Cannot add name to stealer node at {bm.pos} ({bm.lno+1}:{bm.cno})')
                    node = nodes.Stealer()
                case CHARS.group_start:
                    node = nodes.NodeGroup(*tuple(compile_expression(bm, _stop=CHARS.group_stop, _in_group=True)))
                case CHARS.group_nospace_start:
                    node = nodes.NodeGroup(*tuple(compile_expression(bm, _stop=CHARS.group_nospace_stop, _in_group=True)))
                case CHARS.union_start:
                    node = nodes.NodeUnion(*tuple(compile_expression(bm, _stop=CHARS.union_stop, _in_group=False)))
                case CHARS.context_start:
                    bm.match(PATTERNS.discard)
                    if (m := bm.match(PATTERNS.string)) is not None:
                        node = nodes.Context(codecs.escape_decode(m.group(1))[0])
                    else:
                        if (m := bm.match(PATTERNS.context)) is not None:
                            node = nodes.Context(codecs.escape_decode(m.group(1))[0])
                        else:
                            raise SyntaxError(f'Expected either "string" pattern {PATTERNS.string.pattern} or only alphanumeric characters or underscore at {bm.pos} ({bm.lno+1}:{bm.cno})')
                    bm.match(PATTERNS.discard)
                    if (c := bm.read(1)) != CHARS.context_stop:
                        raise SyntaxError(f'Expected context stop {CHARS.context_stop!r}, not {bytes(c)!r} at {bm.pos} ({bm.lno+1}:{bm.cno})')
                case _ as c:
                    if c != _stop:
                        raise SyntaxError(f'Expected node--unknown character {bytes(c)!r} at {bm.pos} ({bm.lno+1}:{bm.cno})')
                    if name is not None:
                        raise SyntaxError(f'Reached stop-mark {_stop!r}, but expected node after name-pattern')
                    return
        # finish and yield
        bm.match(PATTERNS.discard)
        node.name = name
        yield node
