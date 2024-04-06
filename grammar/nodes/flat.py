#!/bin/python3

'''Flat nodes that do not contain other nodes'''

#> Imports
import re
from enum import Enum

from . import GrammarNode

from ..patterns.buffermatcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('PatternNode',)

class PatternNode(GrammarNode):
    '''
        References a pattern

        `return_mode` affects the return value of `.match()`:
          - `MATCH`: return the `re.Match` object, `<match>`
          - `DICT`: return a dict of the named capture groups, `<match>.groupdict()`
          - `SEQ`: return a tuple of the capture groups, `<match>.groups()`
          - `FULL`: return the entirety of the matching bytes, `<match>.group(0)`
    '''
    __slots__ = ('failure', 'pname', 'patt')

    ReturnMode = Enum('ReturnMode', ('MATCH', 'DICT', 'SEQ', 'FULL'))

    pname: str
    patt: re.Pattern | None
    return_mode: ReturnMode

    def setup(self, *, patt: str) -> None:
        self.failure = Exception('Node was never compiled')
        self.pname = patt
        self.patt = None

    def compile(self) -> None:
        if not self.bound.patterns.is_complete(self.pname):
            self.failure = ValueError(f'Required pattern {self.pname!r} is missing or incomplete')
            return
        self.patt = re.compile(self.bound.patterns[self.pname])
        self.failure = None

    def match(self, on: AbstractBufferMatcher, *, return_mode: ReturnMode) \
    -> object | re.Match | dict[str, bytes] | tuple[bytes, ...] | bytes:
        m = on(self.patt.match)
        if m is None: return self.NOMATCH # -> object
        match return_mode:
            case self.ReturnMode.MATCH: return m # -> re.Match
            case self.ReturnMode.DICT: return m.groupdict() # -> dict[str, bytes]
            case self.ReturnMode.SEQ: return m.groups() # -> tuple[bytes, ...]
            case self.ReturnMode.FULL: return m.group(0) # -> bytes
