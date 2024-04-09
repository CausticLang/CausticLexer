#!/bin/python3

#> Imports
import re
import buffer_matcher
from types import SimpleNamespace
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
)
PATTERNS.discard = re.compile(b'((' + PATTERNS.whitespace.pattern + b')|(' + PATTERNS.comment.pattern + b'))+', re.MULTILINE)

CHARS = SimpleNamespace(
    statement_stop = b';',
    group_start = b'(', group_stop = b')',
    group_nospace_start = b'{', group_nospace_stop = b'}',
    union_start = b'[', union_stop = b']',
    stealer = b'!',
)

def compile(bm: buffer_matcher.AbstractBufferMatcher) -> cabc.Generator[tuple[str, nodes.Node], None, None]:
    while True:
        bm(PATTERNS.discard.match)
        if not bm.peek(): return # EOF
        if (m := bm(PATTERNS.statement.match)) is not None:
            yield (m.group(1), nodes.NodeGroup(*tuple(compile_expression(bm))))
        else:
            raise ValueError(f'Expected statement at {bm.pos} ({bm.lno+1}:{bm.cno})')

def compile_expression(bm: buffer_matcher.AbstractBufferMatcher, *, _stop: bytes = CHARS.statement_stop) -> cabc.Generator[nodes.Node, None, None]:
    while True:
        bm(PATTERNS.discard.match)
        # pre-nodes
        if (m := bm(PATTERNS.named.match)) is not None:
            name = m.group(1).decode()
            bm(PATTERNS.discard.match)
        # check for EOF
        c = bm.peek()
        if not c:
            if name is None:
                raise EOFError(f'Reached end of file before stop-mark {_stop!r}')
            raise EOFError('Reach end of file, but expected node after name-pattern')
        else: name = None
        # nodes
        if (m := bm(PATTERNS.string.match)) is not None:
            node = nodes.StringNode(m.group(1))
        else:
            match bm.step():
                case CHARS.group_start:
                    node = nodes.NodeGroup(*tuple(compile_expression(bm, _stop=CHARS.group_stop)))
                case CHARS.group_nospace_start:
                    node = nodes.NodeGroup(*tuple(compile_expression(bm, _stop=CHARS.group_nospace_stop)))
                case CHARS.union_start:
                    node = nodes.NodeUnion(*tuple(compile_expression(bm, _stop=CHARS.union_stop)))
                case _ as c:
                    if c != _stop:
                        raise SyntaxError(f'Expected node--unknown character {bytes(c)!r} at {bm.pos} ({bm.lno+1}:{bm.cno})')
                    if name is not None:
                        raise SyntaxError(f'Reached stop-mark {_stop!r}, but expected node after name-pattern')
                    return
        # post-nodes
        bm(PATTERNS.discard.match)
        if bm.peek() == CHARS.stealer:
            node.is_stealer = True
        # yield node
        node.name = name
        yield node
