#!/bin/python3

'''Flat nodes that do not contain other nodes'''

#> Imports
import re
from enum import Enum

from . import base
from . import exceptions

from . import GrammarMark

from ..buffer_matcher import AbstractBufferMatcher
#</Imports

#> Header >/
__all__ = ('PatternNode',)

class PatternNode(base.NodeWithReturnMode, base.NeverNestedNode):
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

    def setup(self, patt: str, **kwargs) -> None:
        super().setup(**kwargs)
        self.failure = exceptions.NodeNotReadyException(self.name,
            'This node requires a pattern, but has not been compiled')
        self.pname = patt
        self.patt = None

    def compile(self) -> None:
        if self.check_unbound(): return
        if not self.bound.patterns.is_complete(self.pname):
            self.failure = ValueError(f'Required pattern {self.pname!r} is missing or incomplete')
            return
        self.patt = re.compile(self.bound.patterns[self.pname])
        self.failure = None

    def match(self, on: AbstractBufferMatcher, *, return_mode: ReturnMode) \
    -> GrammarMark | re.Match | dict[str, bytes] | tuple[bytes, ...] | bytes:
        m = on(self.patt.match)
        if m is None: return GrammarMark.NO_MATCH # -> GrammarMark
        match return_mode:
            case self.ReturnMode.MATCH: return m # -> re.Match
            case self.ReturnMode.DICT: return m.groupdict() # -> dict[str, bytes]
            case self.ReturnMode.SEQ: return m.groups() # -> tuple[bytes, ...]
            case self.ReturnMode.FULL: return m.group(0) # -> bytes
