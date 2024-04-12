#!/bin/python3

'''Caustic's lexing/grammar framework'''

#> Imports
from pathlib import Path
#</Imports

#> Package >/
__all__ = ('basic_compiler', 'nodes', 'serialize', 'util',
           'Compiler', 'saved_compiler', 'load_compiler', 'save_compiler')

from . import basic_compiler
from . import nodes
from . import serialize
from . import util

from .compiler import Compiler

saved_compiler: Compiler | None = None
def load_compiler(type_: type = Compiler, base_path: Path = Path(__file__).parent, *,
                  file_cache: bool = True) -> Compiler:
    '''
        Loads the advanced grammar compiler using `basic_compiler`,
            and sets `saved_compiler` to it
        If it was already loaded as `saved_compiler`, returns that object
        If `file_cache`, then checks for the file cache as well
    '''
    global saved_compiler
    if saved_compiler is not None: return saved_compiler
    if file_cache:
        pf = base_path/'precompiled_nodes.pkl'
        if pf.is_file():
            saved_compiler = Compiler(serialize.deserialize(pf.read_bytes()), base_path)
            return saved_compiler
    gf = (Path(__file__).parent / 'grammar.cag')
    if not gf.is_file():
        raise FileNotFoundError(f'{gf} does not exist as a file')
    from buffer_matcher import DynamicBufferMatcher #
    saved_compiler = type_(basic_compiler.compile(
        DynamicBufferMatcher(gf.read_bytes())), base_path)
    return saved_compiler

def save_compiler(comp: Compiler, base_path: Path = Path(__file__).parent) -> None:
    '''Saves the compiler to a persistent file'''
    (base_path/'precompiled_nodes.pkl').write_bytes(serialize.serialize(comp.grammar))
