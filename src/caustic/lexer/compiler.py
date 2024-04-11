#!/bin/python3

'''
    Uses `basic_compiler` and `./grammar.cag` to create a
        more advanced/resilient grammar compiler
'''

#> Imports
import re
import codecs
import typing
import warnings
import buffer_matcher
from pathlib import Path
from functools import singledispatch

from . import nodes
from . import basic_compiler
#</Imports

#> Header >/
__all__ = ('builtin_path', 'DEFAULT_GRAMMAR',
           'compile_path', 'compile_file', 'compile_bytes', 'compile_buffermatcher', 'compile_dict',
           'compile_node_name', 'compile_node')

builtin_path = Path(__file__).parent/'grammar.cag'
if builtin_path.is_file():
    DEFAULT_GRAMMAR = basic_compiler.compile(
        buffer_matcher.DynamicBufferMatcher(builtin_path.read_bytes()))
else:
    warnings.warn(f'Builtin grammar file {builtin_path.as_posix()} does not exist')
    DEFAULT_GRAMMAR = None

@singledispatch
def compile(src: Path | typing.BinaryIO | bytes | buffer_matcher.SimpleBufferMatcher | dict, *,
            source: Path | str | None = None, grammar: dict[bytes, nodes.Node] | None = None) -> dict[bytes, nodes.Node]:
    '''Compiles a `Path`, file, `bytes`, or buffer-matcher into a grammar'''
    raise TypeError(f'Cannot compile type of {bad}, must be a Path, file, bytes, or buffer-matcher')

@compile.register
def compile_path(path: Path, *, source: Path | str | None = None,
                 grammar: dict[bytes, nodes.Node] | None = None) -> dict[bytes, nodes.Node]:
    '''Reads a path and compiles its contents'''
    return compile_bytes(path.read_bytes(), source=(path if source is None else source), grammar=grammar)
@compile.register
def compile_file(file: typing.BinaryIO, source: Path | str | None = None,
                 grammar: dict[bytes, nodes.Node] | None = None) -> dict[bytes, nodes.Node]:
    '''Reads a binary file and compiles its contents'''
    if source is None:
        source = Path(file.name)
        if not source.is_file(): source = file.name
    return compile_bytes(file.read(), source=source, grammar=grammar)

@compile.register
def compile_bytes(data: bytes, *, source: Path | str | None = '<bytes>',
                  grammar: dict[bytes, nodes.Node] | None = None) -> dict[bytes, nodes.Node]:
    '''Compiles bytes'''
    if source is None: source = '<bytes>'
    return compile_buffermatcher(buffer_matcher.DynamicBufferMatcher(data), source=source, grammar=grammar)
@compile.register
def compile_buffermatcher(bm: buffer_matcher.SimpleBufferMatcher, source: Path | str | None = '<buffermatcher>',
                          grammar: dict[bytes, nodes.Node] | None = None) -> dict[bytes, nodes.Node]:
    '''Compiles a buffermatcher'''
    if grammar is None: grammar = DEFAULT_GRAMMAR
    if grammar is None:
        raise FileNotFoundError('The default grammar did not exist at module import and as such can not be used')
    grammars = {}
    while (bm.peek(1)):
        while bm.match(nodes.WHITESPACE_PATT) or (grammar[b'COMMENT'](bm) is not nodes.Node.NO_RETURN): pass
        if not (c := bm.peek(1)): break
        stmt = grammar[b'STATEMENT'](bm)
        if stmt is nodes.Node.NO_RETURN:
            raise SyntaxError(f'Unexpected character: {c!r}')
        grammars[stmt['name']] = stmt['expr']
    return compile_dict(grammars)
@compile.register
def compile_dict(data: dict, *, source: Path | str | None = '<dict>', grammar: dict[bytes, nodes.Node] = None) -> dict[bytes, nodes.Node]:
    '''Compiles a dictionary of preprocessed tokens'''
    cnodes = {name: compile_node(b'group', expr) for name,expr in data.items()}
    for node in cnodes.values(): node.bind(cnodes)
    return cnodes

def compile_node_name(name: bytes | str | None, expr: dict) -> nodes.Node:
    '''Compiles a node and names it'''
    node = compile_node(**expr)
    node.name = None if name is None else name if isinstance(name, str) else name.decode()
    return node
    
def compile_node(type: typing.Literal[b'group', b'group_ws_sensitive', b'union', b'range', b'range_ws_sensitive',
                                      b'string', b'pattern', 'stealer', b'context', b'noderef'], val: typing.Any | None = None) -> nodes.Node:
    '''Compiles a single node (or recursive nodes) given its type and a value'''
    match type:
        case b'group':
            return nodes.NodeGroup(*(compile_node_name(**n) for n in val))
        case b'group_ws_sensitive':
            return nodes.NodeGroup(*(compile_node_name(**n) for n in val), keep_whitespace=True)
        case b'union':
            return nodes.NodeUnion(*(compile_node_name(**n) for n in val))
        case b'range':
            return nodes.NodeRange(compile_node_name(**val['node']), int(val['min'] or 0), int(val['max']) if val['max'] else None)
        case b'range_ws_sensitive':
            return nodes.NodeRange(compile_node_name(**val['node']), int(val['min'] or 0), int(val['max']) if val['max'] else None, keep_whitespace=True)
        case b'string':
            return nodes.StringNode(codecs.escape_decode(val)[0])
        case b'pattern':
            flags = re.NOFLAG
            for k,f in basic_compiler.RE_FLAGS.items():
                if k in val['flags']: flags |= f
            return nodes.PatternNode(re.compile(val['pattern'], flags), int(val['group']) if val['group'] else None)
        case b'stealer':
            return nodes.Stealer()
        case b'context':
            ctx = val.get('raw', None)
            if ctx is None:
                ctx = codecs.escape_decode(val['str'])[0]
            return nodes.Context(ctx)
        case b'noderef':
            return nodes.NodeRef(val)
        case _:
            raise TypeError(f'Unknown node type {type!r}')
