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

# LOAD PRECOMPILED GRAMMAR
DEFAULT_GRAMMAR = __import__('pickle').loads(
    __import__('lzma').decompress(
        b'\xfd7zXZ\x00\x00\x04\xe6\xd6\xb4F\x02\x00!\x01\x16\x00\x00\x00t/\xe5\xa3\xe0\r\xd9\x03\x91]'
        b'\x00@\x01\x0ez\xe4,\xe2\xe9\x84\x0f\xcc\xd5\xcd\xd8\x13\x9d\x00=\x12\xea\x8d\x1b~\xfd\xc1\\]3\x10'
        b'\x12\xd5\xc9"\xdfeE\xf1Q\x9d-$_T\xf2Q\xb6b\xe7^\xf8\x8f\xd6\x03,N\xa2+\x03"'
        b'\xec\xc2q6%\xa4\x84\xad\x17\xbb\x0fv\xeb\xe9c\xc5\xc8,\x8d\x1c[\xc7\xc8\xe2tc\xf7\xd9\xe5W'
        b'\x80\x07\x12\xd8s\xa2\x92\xcc\xfb\xab\xdfd#\x8c\xe6\xcbq\xccU(\xf0\xa7\x96\xda\x16R\xbc\xb5\xdf\x1c'
        b'{cj\xd2\xcf\xa6Y\x915/\x18\x92\xc3\x87b\x97\xd6\xf3n\xa3q\x10a\xe4* \x02\x85"\xaa'
        b'1\xb5\x85I\\Y2\n\x1a\x81\x11\x1f\xb4\x9a?\x05\xeeA\xe8_\x10\x06\xbf\xb8\xe5\xce\xb0\xcf\x06\xbb'
        b'i\xae\xf0\x86\xfdPL!/\x83\x01Dp\x13\xe2\xd2)@\xc6\x96\x08}B0h\xaa\xe7\x15&5'
        b'\xa5Mr8\xd91j\x83\xfb\xe1\x1e\xb5\xbd\xd1A\x9d\x16N\x9a\x9fu\xebw\xa5\xb8,\xac>\xbe\xac'
        b'\xc5\x8a\xbd*\xc96[9\xb8\xfe\x86]\xfaP\x1b\x1b\x83`\xdcy\x7f\xd7\xffC\x88s\xfa\x9c>l'
        b'\xa1dtw\xbb\x97\xbe*\x9aI\xd5r\xed\xeb\xfb\x89X\xb9\x89k%\x0b\xe9^\x03\xd0A\xd0A\xa5'
        b"\x9a\x82\x97\x15*'\x01k\x8e\xc4\xb2\x0b\xd5\xedF\r\xe1\xac\x91\x10\xa08<\xe9\x1fC\xf9\xa8-\xab"
        b'\x1f\x17\xd3\xe1\x99\r\xf8iz\xffa\xa9FQ"}b]?<D\xd5\xdf}\x9c\xe6\xfe\x1aTH'
        b"\xb0u\x12\x81\xff\xc5m\xbc\xdf(i]\x89\x81\xbf\x13\xbf '\xe4\x94\x8dm\x9c\xcb)i\xbfc\x89"
        b'?\x1b\xda\xe4\x9aM\xb0Gn0o\xc2\xa7\x9975\xd4d\x12\x86\xe4\xa8"O_\x81(\xb3q\x87'
        b'\xeeF\xe8\xe9\xaf\xcf\xb3\xa4\xc8\xb9\xc8u96\x8c\xd7{\xa0\x1e+\xbbo\xb1\xb2*\xb3\x14\x0b\xdc\xab'
        b'\xee\xf8_\xea\t\x97\x04\x1b\x9d\x029&\xa5y\x17\xc2\xd2\x10\xcf\xc2\xcdU_\xf5(Q\x11\xc3\xb9\xac'
        b'\x07%\xcc\x9ca}w\x94&\x9d\x07q\x8fb!v\xb61\xbe$E\x0b\x90\x1f,H\xfc\xc1\x9e\xe5'
        b"B|mP\xd4h8p\xb2\xfd\xaf\x1e\xc2`E\x00\xd4\xb6\x9eUc\x9dA'\xb8\xda\xe1l\xf5\x03"
        b"\xe1\xd98\xd3'\xc0b\xcc\xd4`\xbbns\xd1\xf5'\xcf\x94\x10zk9\xb0\xfe~LOy\xfd`"
        b'\xc7\xdc9k\x86\xe2\xbe\x00\xb3\x17Y=c\xf4\\\xdf\xa4\xbd\xe4\xf6\xed\x8c\x01\xda\xa1;\x99(\xde\xcc'
        b'\xf4\xfd8B\xd4\xb46\x92\xce\xea\xf2ST\xc36\x8ep>\x97\x14\xfa\xd3\xbf=;\xba\x1a\xd9\xa0\x01'
        b'\xd8\x04\xe4\x84ab+\x05\xda\x8a&\x11\xf8\x89\xa7:\n\xbc\x13\x89\xfd_(w\x05_t\x9c\xfbm'
        b'n\xe5\xf0\xe0B\xfb\xe4\xda\x90\xb4TB\x15M\xb9%\tX\x81p)\xc6\xeeV\x1a.\xa0I\xa3\x80'
        b'\xda\x07\xfa\x0b.\x89\x8bk\xb6\x06G}b?\xe4\x8bu\xf8\xda\xc5yv\x1f"\xaa\t\x05\x86\x8f '
        b'$\xde\xedY\xf806n\xbd\x99\xaf\x06_\xdb\xb5\x97\xb4\x9e\xcf~\x84\x7f\x99:\xf6\xdd\xc5\xe2\xa4\xc1'
        b'\xfeO\xea\xbf\xba\x9a\xe3"\x91M\xcdK\xd4}\xdf\xa1\xc3\x88\xb0\xec\x88\r\xb6I\xdblyZ\xe4\x06'
        b'\xdbN\xc0["\x14c\xb0\x1cc\xb2\xc6(jo\xc9\xae\x9f^[\xc4\x12\xab\xb7\xdf\x9d0\xe4$\xa7'
        b'n\xf3r\x87X\xa3\xf7\x88\x9b\xe03\xa5Q\xa5\xf8,`\xbe#G&l\xc2\xf8`\x94E\xd5\xf6V'
        b'\xf6tG.\x14\xcc\xd3\xa3\x89\xec\x1b\xfb\xf6s\x0eo\x069\x0b\t\x81\x80(\x18.~\xf6\xf6\x97D'
        b']\xcf\xb6\xb86\x03\xac\x94\x80\xdb\xc6\xff\x92\xbb\\F-\x16\x1a(\xab\xceJ{\r\xb7\xc7B,\xdb'
        b'\xcfZ\xc0<J\x87\x89#R4\xf5.x\x00\x00\x00\x00\x00\xba\x8b\xc3\xc1\x81\xa1\xb1v\x00\x01\xad\x07'
        b'\xda\x1b\x00\x00\x91\x1fm\x8d\xb1\xc4g\xfb\x02\x00\x00\x00\x00\x04YZ'
    )
)

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
    imports = {}; includes = {}
    try:
        while (bm.peek(1)):
            while bm.match(nodes.WHITESPACE_PATT) or (grammar[b'COMMENT'](bm) is not nodes.Node.NO_RETURN): pass
            if not bm.peek(1): break
            if (p := grammar[b'PRAGMA'](bm)) is not nodes.Node.NO_RETURN:
                match p['type']:
                    case b'import' | b'include':
                        f = Path(p['args'].decode())
                        if not f.is_absolute():
                            if isinstance(source, Path) and (nf := (source.parent / f)).is_file(): f = nf
                            elif (nf := (Path.cwd() / f)).is_file(): f = nf
                            elif (nf := (builtin_path.parent / f)).is_file(): f = nf
                            else: raise FileNotFoundError(f'Cannot parse include: {f}')
                        try: (includes if p['type'] == b'include' else imports).update(compile(f))
                        except Exception as e:
                            e.add_note(f'In {p["type"].decode()}')
                            raise e
                    case _ as t:
                        raise TypeError(f'Unknown pragma type {t!r}')
                continue
            stmt = grammar[b'STATEMENT'](bm)
            if stmt is nodes.Node.NO_RETURN:
                raise SyntaxError(f'Unexpected character: {c!r}')
            grammars[stmt['name']] = stmt['expr']
    except Exception as e:
        e.add_note(f'Whilst parsing grammar from: {"<buffermatcher>" if source is None else source}')
        e.add_note(f'At position {bm.pos} ({bm.lno+1}:{bm.cno})')
        raise e
    grammars = compile_dict(grammars, source=source, grammar=grammar) | includes
    bind_nodes(grammars)
    return grammars | imports
@compile.register
def compile_dict(data: dict, *, source: Path | str | None = '<dict>', grammar: dict[bytes, nodes.Node] = None) -> dict[bytes, nodes.Node]:
    '''Compiles a dictionary of preprocessed tokens'''
    try:
        cnodes = {name: compile_node(b'group', expr) for name,expr in data.items()}
    except Exception as e:
        e.add_note(f'Whilst compiling grammar from: {"<dict>" if source is None else source}')
        raise e
    bind_nodes(cnodes)
    return cnodes

def bind_nodes(nodes: dict[bytes, nodes.Node]) -> None:
    '''Cross-binds all nodes'''
    for node in nodes.values(): node.bind(nodes)

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


# BIND PRECOMPILED DEFAULT_GRAMMAR
bind_nodes(DEFAULT_GRAMMAR)