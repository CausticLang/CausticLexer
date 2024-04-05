#!/bin/python3

'''
    Provides Buffer matchers
    See `help(AbstractBufferMatcher)`
'''

#> Imports
import re
import typing
from abc import ABC, abstractmethod, abstractproperty
from functools import wraps
from collections import abc as cabc
#</Imports

#> Header >/
__slots__ = ('AbstractBufferMatcher', 'BufferMatcher_DynamicLCNo', 'BufferMatcher_StaticLCNo')

class AbstractBufferMatcher(ABC):
    '''
        Efficiently matches slices of bytes,
            keeping track of line and column numbers
    '''
    __slots__ = ()

    @abstractproperty
    def buffer(self) -> cabc.Buffer: 'The underlying `memoryview`'
    @abstractproperty
    def data(self) -> bytes: 'The `bytes` object corresponding to the `.buffer`
    @abstractproperty
    def pos(self) -> int: 'The current working index'

    @abstractproperty
    def lno(self) -> int: 'The current line number'
    @abstractproperty
    def cno(self) -> int: 'The current column number'

    @abstractmethod
    def __call__(self, func: cabc.Callable[[cabc.Buffer], re.Match | None]) -> re.Match | None:
        '''
            Executes the function, advancing the position by the size
                of the match result
            The most commonly passed function is `<re.Pattern>.match`
        '''
    @abstractmethod
    def step(self, amount: int = -1, *, allow_breakout: bool = False) -> cabc.Buffer:
        '''
            Step through the buffer by `amount`
            If `amount` would bring the position below 0 or about the buffer's
                maximum length, an `IndexError` is raised unless `allow_break`
        '''
        
    
class BufferMatcher_DynamicLCNo(AbstractBufferMatcher):
    '''
        A `BufferMatcher` implementation
        Dynamically calculates `.lno` and `.cno` via properties
    '''
    __slots__ = ('buffer', 'data', 'pos')

    buffer: cabc.Buffer
    data: bytes
    pos: int

    @property
    def lno(self) -> int:
        return self.data.count(b'\n', 0, self.pos + 1)
    @property
    def cno(self) -> int:
        try: line = self.data.rindex(b'\n', 0, self.pos + 1)
        except ValueError: line = 0
        return self.pos - line

    def __init__(self, data: bytes):
        self.buffer = memoryview(data)
        self.data = data
        self.pos = 0

    def __call__(self, func: cabc.Callable[[cabc.Buffer], re.Match | None]) -> re.Match | None:
        m = func(self.buffer[self.pos:])
        if m is None: return None
        self.pos += m.end()-1
        return m
    def step(self, amount: int = -1, *, allow_breakout: bool = False) -> cabc.Buffer:
        newp = self.pos + amount
        if (not allow_breakout) and (newp < 0) or (newp > len(self.data)):
            raise IndexError('Cannot step by an amount that would over/underflow')
        buff = self.buffer[slice(newp, self.pos) if amount < 0 else slice(self.pos, newp)]
        self.pos = (len(self.data) + newp) if newp < 0 else newp
        return buff

class BufferMatcher_StaticLCNo(BufferMatcher_DynamicLCNo):
    '''
        A `BufferMatcher` implementation
        Calculates and stores `.lno` and `.cno` after matching or stepping
    '''
    __slots__ = ('lno', 'cno')

    cno: int
    lno: int

    def __init__(self, *args, **kwargs):
        self.cno = self.lno = 0
        super().__init__(*args, **kwargs)

    @wraps(BufferMatcher_DynamicLCNo.__call__)
    def __call__(self, *args, **kwargs) -> typing.Any:
        m = super().__call__(*args, **kwargs)
        if m is None: return None
        if lc := m.group(0).count(b'\n'):
            self.lno += lc
            self.cno = m.end() - m.group(0).rindex(b'\n')
        return m
    @wraps(BufferMatcher_DynamicLCNo.step)
    def step(self, *args, **kwargs) -> typing.Any:
        buff = super().step(*args, **kwargs)
        if buff.nbytes:
            self.lno = super().lno
            self.cno = super().cno
        return buff
