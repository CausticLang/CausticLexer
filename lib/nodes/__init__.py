#!/bin/python3

'''Implements grammar nodes'''

#> Imports
import functools
from enum import IntEnum

from . import exceptions

from .. import __init__ as _root
#</Imports

__all__ = ('GrammarNode', 'GrammarMark', 'base', 'flat', 'nested', 'meta') + exceptions.__all__

#> Header
class GrammarMark(IntEnum):
    '''Sentinals for irregular returns of `GrammarNode.match()`'''
    NO_MATCH  = 0b000
    INDENT    = 0b001
    DEDENT    = 0b010
    NO_CHANGE = 0b011 # INDENT + DEDENT
#</Header

#> Package >/
from .exceptions import *

from .base import GrammarNode
from . import base
from . import flat
from . import nested
from . import meta
