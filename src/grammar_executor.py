#!/bin/python3

#> Imports
import re
import typing
from ast import literal_eval
from enum import Enum
from collections import abc as cabc

import buffer_matcher
import grammar_compiler as compiler
#</Imports

#> Header >/
__all__ = ()

class Executor:
    '''...'''
    __slots__ = ('master', 'sequence', 'is_union', 'is_target')

    master: 'Master'
    sequence: list[compiler.GrammarTypes]
    is_union: bool
    is_target: bool

    def __init__(self, *seq: compiler.GrammarTypes | compiler.Markers | tuple, is_union: bool = False, is_target: bool = False):
        self.is_union = is_union
        self.is_target = is_target
        self.sequence = []
        seq = iter(seq)
        for e in seq:
            if isinstance(e, compiler.Markers):
                match e:
                    case e.UNION | e.TARGET:
                        try: n = next(seq)
                        except StopIteration as sie:
                            sie.add_note(f'Whilst attempting to resolve marker {e!r}')
                            raise sie
                        self.sequence.append(type(self)(*n, is_union=e is (e.UNION), is_target=(e is e.TARGET)))
                    case e.STEALER: self.sequence.append(e)
                    case _:
                        raise TypeError(f'Cannot resolve sequence element {e!r}')
            elif isinstance(e, bytes):
                print(self, 0, e)
                self.sequence.append(e.decode('unicode_escape').encode())
                print(1, self.sequence[-1])
            elif isinstance(e, tuple):
                self.sequence.append(type(self)(*e))
            else: self.sequence.append(e)

    def _test(self, s: typing.Any, data: buffer_matcher.AbstractBufferMatcher, *, _is_stealer: bool) -> tuple[typing.Any | None, bool | None]:
        if isinstance(s, type(self)):
            return (s(data, _is_stealer=_is_stealer), s.is_target)
        match s:
            case bytes():
                if data.peek(len(s)) == s: return (s, self.is_target)
                if _is_stealer:
                    raise ValueError(f'Expected string {s!r} at line {data.lno} column {data.cno}')
            case re.Pattern():
                if (m := data(s.match)) is not None: return (m, self.is_target)
                if _is_stealer:
                    raise ValueError(f'Expected pattern {s!r} at line {data.lno} column {data.cno}')
            case compiler.Markers.STEALER:
                raise TypeError('STEALER marker disallowed here')
            case _: raise TypeError(f'Cannot handle sequence element {s!r}')
        return (None, None)
    def __call__(self, data: buffer_matcher.AbstractBufferMatcher, *, _is_stealer: bool = False) -> list[typing.Any] | typing.Any | None:
        if self.is_union:
            for s in self.sequence:
                if s is compiler.Markers.STEALER:
                    raise TypeError('STEALER marker disallowed as union element')
                if (res := self._test(s, data, _is_stealer=_is_stealer)[0]) is not None:
                    return res
            return None
        result = []
        save = data.save_loc()
        for s in self.sequence:
            if s is compiler.Markers.STEALER:
                _is_stealer = True
                continue
            res,target = self._test(s, data, _is_stealer=_is_stealer)
            if res is None:
                data.load_loc(save)
                return None
            if target: result.append(res)
        return result

class Master:
    '''...'''
    __slots__ = ('grammar',)

    grammar: dict[bytes, tuple[compiler.GrammarTypes | typing.Self]]

    def __init__(self, grammar: cabc.Mapping[bytes, compiler.GrammarTypes | tuple] |
                                cabc.Iterable[tuple[bytes, compiler.GrammarTypes | tuple]]):
        self.grammar = {k: (Executor(*g) if isinstance(g, tuple) else Executor(g))
                        for k,g in (grammar.items() if isinstance(grammar, cabc.Mapping) else grammar)}


with open('./grammar.cag', 'rb') as f:
    bm = buffer_matcher.BufferMatcher_DynamicLCNo(f.read())

from pprint import pprint
c = dict(compiler.compile(bm))
pprint(c)
m = Master(c)

with open('./test.cas', 'rb') as f:
    bm = buffer_matcher.BufferMatcher_DynamicLCNo(f.read())
i = (m.grammar[b'STRING'](bm))
