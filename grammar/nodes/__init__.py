#!/bin/python3

'''Implements grammar nodes'''

#> Imports
import functools
from enum import Enum, auto

from . import exceptions

from .. import __init__ as _root
#</Imports

__all__ = ('GrammarNode', 'GrammarMark', 'base', 'flat', 'nested', 'meta') + exceptions.__all__

#> Header
class GrammarMark(Enum):
    '''Sentinals for irregular returns of `GrammarNode.match()`'''
    NO_MATCH = auto()
#</Header

#> Package >/
from .exceptions import *

from .base import GrammarNode
from . import base
from . import flat
from . import nested
from . import meta
