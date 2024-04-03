#!/bin/python3

'''
    Provides a parser for Caustic's configuration files (`.ccfg`)
    The syntax for CCfg files is based on INI, and uses Python's `ConfigParser`,
        although with a few tweaks, such as the introduction of pragmas
'''

#> Imports
import sys
import typing
import configparser
from os import PathLike
from pathlib import Path
from collections import abc as cabc
#</Imports

#> Header >/
__all__ = ('CCfgParsingError', 'CCfgNotFoundError', 'CCfgParser')

class CCfgParsingError(Exception):
    '''For when an error occurs whilst parsing Caustic config files'''
    __slots__ = ()
class CCfgNotFoundError(CCfgParsingError):
    '''For when a config file (usually from a "load" or "include" pragma) was not found or is not a file'''
    __slots__ = ()

class CCfgParser(configparser.ConfigParser):
    '''Parser for Caustic configuration (`.ccfg` files)'''

    SUFFIX = '.ccfg'

    include_dirs: list[Path]
    pragma_pfx: str
    debug_lvl: typing.Literal[*range(-1, 4)]

    def __init__(self, *args, include_dirs: typing.Iterable[Path] = (), pragma_pfx: str = '$', debug: typing.Literal[*range(-1, 4)] = 1,
                 allow_no_value: bool = True,
                 delimiters: tuple[str, ...] = ('=',), comment_prefixes: tuple[str, ...] = ('#',),
                 interpolation: configparser.Interpolation | object | None = None, **kwargs):
        self.include_dirs = list(include_dirs)
        self.pragma_pfx = pragma_pfx
        self.debug_lvl = debug
        super().__init__(*args, allow_no_value=allow_no_value, delimiters=delimiters,
                         comment_prefixes=comment_prefixes, interpolation=interpolation, **kwargs)

    def debug(self, lvl: typing.Literal[*range(0, 4)], *args, file: typing.TextIO = sys.stderr, **kwargs) -> None:
        '''Prints a debugging message according to the `.is_debug` attribute'''
        if self.debug_lvl < lvl: return
        print(f'CCfgParser<{lvl}/{self.debug_lvl}>', *args, file=file, **kwargs)

    def load(self, src: str | PathLike) -> None:
        '''Loads a path, preprocessing it beforehand'''
        self.debug(1, f'.load() issued for source {src!r}')
        path = self.resolve_path(src, None)
        self.read_string('\n'.join(self.preprocess_string(path.read_text(), source=path.as_posix())),
                         source=path.as_posix())
        self.debug(2, f'.load() completed for source {src!r}')
    def resolve_path(self, path: str | PathLike, source: Path | None = None) -> Path:
        '''
            Resolves a relative path based on `.include_dirs`, `source`, and CWD
            Absolute paths are returned as-is
            A `CCfgNNotFoundError` is raised if the path doesn't exist
        '''
        path = Path(path) # path path path
        if path.is_absolute():
            self.debug(2, f'{npath!r} is absolute')
            return path # no need to fix
        def tjoin(parent: Path) -> Path | None:
            npath = parent / path
            self.debug(3, f'Checking {npath.as_posix()!r}')
            if npath.is_file():
                self.debug(2, f'{npath.as_posix()!r} is a file, success')
                return npath
            npath = npath.parent / f'{path.name}{self.SUFFIX}'
            self.debug(3, f'Checking {npath.as_posix()!r}')
            if npath.is_file():
                self.debug(2, f'{npath.as_posix()!r} is a file, success')
                return npath
            return None
        for par in self.include_dirs: # relative to include dirs
            if (p := tjoin(par)) is not None: return p
        if source is not None: # relative to source
            if source.is_file(): source = source.parent
            if (p := tjoin(source)) is not None: return p
        if (p := tjoin(Path())) is not None: return p # relative to CWD
        raise CCfgNotFoundError(f'Could not resolve {path.as_posix()!r} to any include_dirs'
                                f'{"" if source is None else f", source {source.as_posix()!r},"} or CWD')
    def preprocess_string(self, string: str, source: str | None) -> cabc.Generator[str, None, None]:
        '''Preprocesses pragmas in a string'''
        self.debug(2, f'.preprocess_string() issued for string of length {len(string)} from {source or "<unknown source>"}')
        for l in string.splitlines():
            self.debug(3, f'Preprocessing line: {l!r}')
            if l.startswith(self.pragma_pfx):
                yield from self.handle_pragma(l[1:], source)
            else: yield l
        self.debug(2, f'.preprocess_string() finished for string of length {len(string)} from {source or "<unknown source>"}')
    def handle_pragma(self, pragma: str, source: str | None) -> cabc.Generator[str, None, None]:
        '''Handles pragmas from `.preprocess_string()`'''
        self.debug(1, f'Handling pragma: {pragma!r}')
        match pragma.split(':', 1):
            case ('load', path):
                self.debug(0, f'Pragma "load" issued for {path!r}')
                path = Path(path) # path path path
                if (source is not None) and (not path.is_absolute()):
                    path = source / path
                self.load(path)
            case ('print', arg):
                print(f'{source or "<unknown source>"}: {arg}', file=sys.stderr)
            case ('error', arg):
                raise CCfgParsingError(f'{source or "<unknown source>"}: {arg}')
            case ('include', path):
                self.debug(0, f'Pragma "include" issued for {path!r}')
                yield from self.preprocess_string(self.resolve_path(path).read_text(), source=path)
            case ('include_raw', path):
                self.debug(0, f'Pragma "include_raw" issued for {path!r}')
                yield self.resolve_path(path).read_text().splitlines()
            case _:
                raise CCfgParsingError(f'Cannot resolve pragma directive {pragma!r} from {source or "<unknown source>"}')
