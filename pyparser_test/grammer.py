#!/bin/python3

'''Stores grammer for Caustic'''

#> Imports
import typing
from dataclasses import dataclass, field

import pyparsing as pypr
#</Imports

#> Header >/
__all__ = ('Grammer',)

# Helpers
_dcbuild = dataclass(kw_only=True, slots=True, weakref_slot=True)

class _DCFromDMixin:
    __slots__ = ('__subclasses')

    def __init_subclass__(cls):
        fields = getattr(cls, '__dataclass_fields__', None)
        if fields is None: return
        cls.__subclasses = {fn: fv.type for fn,fv in fields.items()
                            if isinstance(fv.type, type) and issubclass(fv.type, _DCFromDMixin)}

    @classmethod
    def _convert_v(cls, av: tuple[str, typing.Any]) -> tuple[str, typing.Any]:
        if av[1] is None: return (av[0], None)
        if av[0] in cls.__subclasses: return (av[0], cls.__subclasses[av[0]].from_dict(av[1]))
        return av

    @classmethod
    def from_dict(cls, d: dict) -> typing.Self:
        return cls(**dict(map(cls._convert_v, d.items())))

# Types
type OptionalToken = pypr.Token | None

@_dcbuild
class Grammer(_DCFromDMixin):
    '''Stores grammer for Caustic'''

    # Statements
    @_dcbuild
    class Statements(_DCFromDMixin):
        '''Stores statement(-like) grammer for Caustic'''
        pragma: OptionalToken
    statements: Statements
    # Expressions
    @_dcbuild
    class Expressions(_DCFromDMixin):
        '''Stores expression grammer for Caustic'''
        identifier: pypr.Token
    expressions: Expressions
