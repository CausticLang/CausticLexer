#!/bin/python3

'''
    Parses Caustic Grammer (`.cgram`) files
    Also handles pragma grammer changes
'''

#> Imports
import sys
from os import PathLike
from ast import literal_eval
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
#</Imports

#> Header >/
__all__ = ('exceptions', 'DEFAULT_GRAMMER', 'Grammer')

# Exceptions
class GrammerException(Exception):
    '''Base class for Grammer-related exceptions'''
    __slots__ = ()
class GrammerLoadingError(GrammerException):
    '''A generic base-class for grammer loading errors'''
    __slots__ = ('source',)

    source: str | None

    def __init__(self, *args, source: str | None, **kwargs):
        self.source = source
        super().__init__(*args, **kwargs)
class GrammerNotFoundError(GrammerLoadingError):
    '''
        For when an "include" pragma or `.apply()` method
            references a path that does not exist as a file
    '''
    __slots__ = ('target',)

    target: PathLike | str

    def __init__(self, *args, target: PathLike | str, **kwargs):
        self.target = target
        super().__init__(*args, **kwargs)
class GrammerSyntaxError(GrammerLoadingError):
    '''For when a grammer fails to load due to incorrect syntax'''
    __slots__ = ()
class GrammerPragmaSyntaxError(GrammerSyntaxError):
    '''For when a pragma fails to parse due to incorrect syntax'''
    __slots__ = ()

exceptions = SimpleNamespace(
    GrammerException=GrammerException,
    GrammerLoadingError=GrammerLoadingError,
    GrammerNotFoundError=GrammerNotFoundError,
    GrammerSyntaxError=GrammerSyntaxError,
    GrammerPragmaSyntaxError=GrammerPragmaSyntaxError,
)

# Grammer
DEFAULT_GRAMMER = SimpleNamespace()

class Grammer:
    '''Stores and loads grammer from `.cgram` files and pragmas'''
    __slots__ = ('grammer', 'include_dirs', 'sources')

    grammer: SimpleNamespace

    include_dirs: set[Path]
    sources: dict[str, Path]

    def __init__(self, *include_dirs: str | PathLike, add_cwd: bool = True):
        self.include_dirs = list(map(Path, include_dirs))
        if add_cwd and (Path('.') not in self.include_dirs):
            self.include_dirs.insert(0, Path('.'))
        self.sources = {}
        self.grammer = deepcopy(DEFAULT_GRAMMER)

    def load(self, file: PathLike | str, source: str | None = None) -> None:
        '''
            Loads the grammer from `path`, using `.apply()`
            If `path` is a string (isn't a `PathLike`), and does not start with `/` or `.`,
                then it is tried from each of `.include_dirs`
        '''
        # resolve include-dirs if needed for include-relative paths
        if isinstance(file, PathLike) or file.startswith('/') or file.startswith('.'):
            path = Path(path) # path path path
        else:
            for incdir in self.include_dirs:
                if (incdir/file).is_file():
                    path = incdir/file
                    break
            else:
                raise GrammerNotFoundError(f'Could not resolve "{file}" from any included directories',
                                           target=file, source=source)
        # read file and apply grammer
        try: grammer = path.read_text()
        except IsADirectoryError:
            raise GrammerNotFoundError(f'Could not read grammer from "{path}" as it is a directory',
                                       target=path, source=source) from None
        except FileNotFoundError:
            raise GrammerNotFoundError(f'Could not read grammer from "{path}" as it does not exist',
                                       target=path, source=source) from None
        except Exception:
            raise GrammerException(f'Could not read grammer from "{path}"')
        self.apply(grammer, source=file)

    def _convert_val(self, val: str) -> object:
        '''
            Public function for converting given strings to values
            Prepended with `_` to prevent usage as a pragma
        '''
        val = val.strip()
        if val.startswith('/'): raise NotImplementedError # regex
        if val.lower() == 'disable': return False
        if val.lower() == 'enable': return True
        try: return literal_eval(val)
        except Exception:
            raise GrammerSyntaxError(f'Cannot parse value: {val!r}', source=None)
    def apply(self, grammer: str, source: str | None = None) -> None:
        '''Loads the grammer as a string from `grammer`'''
        for s in grammer.splitlines():
            if not (s := s.strip()): continue # strip whitespace and skip non-statements
            if s.startswith('$'): # handle pragmas
                self.pragma(s[1:], source=source)
                continue
            if s.startswith('#'): continue # handle comments
            try: name,val = s.split(':', 1) # extract name and value
            except ValueError:
                raise GrammerSyntaxError(f'Could not parse statement {s!r}', source=source)
            try: val = self._convert_val(val)
            except GrammerSyntaxError as e:
                e.source = source
                raise e
            self.sources[name] = source
            name = name.split('.')
            t = self.grammer
            for n in name[:-1]:
                if not hasattr(t, n):
                    setattr(t, n, SimpleNamespace())
                t = getattr(t, n)
            setattr(t, name[-1], val)

    # pragmas
    def pragma(self, pragma: str, source: str | None = None) -> None:
        '''Handles a "$" / pragma statement in a grammer'''
        if not pragma[0].isalpha():
            raise GrammerPragmaSyntaxError(f'Pragma directives beginning with non-alphabetical characters are disallowed: {pragma!r}', source=source)
        pragma = pragma.split(' ')
        pmeth = getattr(self, pragma[0], None)
        if pmeth is None:
            raise GrammerPragmaSyntaxError(f'Pragma directive "{pmeth}" not found')
        pmeth(*pragma[1:], source=source)
    ## pragma directives
    def print(self, *args, source: str | None = None) -> None:
        '''Prints a message to stderr'''
        print(*args, file=sys.stderr)
    def fail(self, *args, source: str | None = None) -> None:
        '''Raises a `GrammerException`'''
        raise GrammerException(*args)
