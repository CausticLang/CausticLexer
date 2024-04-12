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
from .serialize import deserialize as __deserialize
DEFAULT_GRAMMAR = _deserialize(__import__('lzma').decompress(
    b'\xfd7zXZ\x00\x00\x04\xe6\xd6\xb4F\x02\x00!\x01\x16\x00\x00\x00t/\xe5\xa3\xe0\x0c\xa4\x03<]'
    b'\x00@\x01\x0ew{q\xcb `\xff\xc2\xb3\xc6Y\x9f\xa5\xc7uf\xfb\xd3\x89>\xb9!\x7flF\xad'
    b'+\xaf\x8b\xbc\xe8\xe8\xff1J\x11m"\x9bu*\x9f\xaawX?\xeeFs\x00\x13\xca3\xa6\xb0\xcb'
    b'rt\xd2\xd0P\xc2~>\xac\xefy>@\xf3\xe1\xed\x82y\x06\xca\x06\x0e\x06\x95N\xf7\xca\xb2?\xe1'
    b'\xff\x87\xa1\xd7szC\x1c\xfe\x841j\x05\xea9\x05<\xc3\x0b\xf1\x95X\xff\xcf\x1fgAb\t\x85'
    b' [\x16\xd6\xa0\xfe7N\xd9\xe5\xf1Cu\xff\xa9\x91\xba\xf3\x12\xf8\xd4s\xc9w\x9f\x85t\x9ehj'
    b'\n.\x02\x9cX\x07\x08\xcfV2\x95\xa9\xa9\x89\x8eEfy }\xc1\x86\x88\xe1B[\xc1\xf9\x87\xdd'
    b"'a\x92\xa3[l\xd72\x18p\xec@J\xddG\\@y\xa1\xed\x17\xd5\xb0H5ni[mn"
    b'\xb2n\xf2<\xce\xf0]_`\x00\x04\x95\x8fW\x14\x13\x84\xb3\x00\xc9\xbf_\x99r\x91\xf5^\x0e\xf3\xf4'
    b'7]\xc6\xab\x9d4,\x13\x1b\x14\xae\xfc\x90\x10\xa93V\xa8\xc5\t\xba1\x1e$Q\xba\xf2\x9d\x9e\x15'
    b'\x8e&\xa3\xfd"&4\xca1%\xdf\xd7\nA\xfa(\xce\x07\xd9v\xe7\x18T\xa1#\x0b><_\xe7'
    b"\x87\x01\xa7\x92-\\\x8b\x15\xfb%50\x18\x8e;5p'C_\xc2LF~\xb2{\xef/\xb5\xe8"
    b'\x0c8\xaa~T$J\xda\x0f\x86\x15\x13\xfc\x82\xb6\xfa\xa19\x07\x83Fe\x92\x96\xc4\x11\x15J\xfb\xa1'
    b'\xd4\xee\xdd\x13`f\xa2\xc4.\xb9S\xbc\xae\xffOf\xd6\x13mmB$\x1aJ\x85~ \xfc\x89\xe8'
    b'\xfc<\x04\x1a\xc6\xf92\xfa>\xb0\xc6\x82\xcd_:\xe3"$n\xfe\xb3\xd3\xc1\xd49\x13\xf0\xdeup'
    b'\xb2N+x\x97\x9dYY\x02\x08Pe\x14t\xe6\x9f\xd4\x8di\x94\x0c\x1f|aw\xbcE"\x02n'
    b'\x02\xc6\xd1\xe9_\x9b\x11>[\x18\xff[mG\x1e\xb0\xf7\x95V\xf4\x87W\xe3\x14\xdf\x85\xb2\x02\x00\xb5'
    b'%\xb9\x1dM?A\xc5.p\xe4@\xacv\xa8Y\x8f\x9a)\x9b\x10u\xaf\xa7\xa5\xc5\xa9\xc9\xda\xd5-'
    b'/u\xd3$\xe0\x81!^\xe3g\xcf\xaf\xdfgp"A\xb1\x1f\xcc\xb6`>x\xfe\xc0\x0c9\x1f?'
    b'\x80\xee\x1c\x10\x14\xa1\xbe\xc69\x05\xd1p(\xdc\x8eW\xe1\xc4\x01\x812\x93\x89k\x92p\x87I=\xfc'
    b'\x1f\x15\xbc\xf1\x00@\xa7zH\t\x11P#\x0c\xe6\xc9\xdfv\xfa\xeaE\xadQ\xcc/\xf6 V\xa8\xcf'
    b"\x86\xa7w\xb3\x95\xc3#\xd9\x1f\xa7\x87F\xa4\xc6rS\x83\xbe\xae&\xb9\xad\x9bL\x02\xdc\x81\xd1\xe4'"
    b'\xecB\xe6b\xccu\xf8\xca*R/\x07\xce*~J\xcf\xa2Xo\xd3\x07\xe8\x99\x8c\x17\xe0\x05\x17\xb1'
    b'\x9a\xbbES\xb9N#\x07\xf3\x1dS\xb75*\xc5X\x85Q\xbe\x99\x92B\x82\xc5\x1cn\xc7\xd6/#'
    b'\xe20t\xab\x10k\x1c\xfe\xce\xf7:\x93\xd4\xb6\xbe\xde\xc1\xbd~\xf5\x81w\x97bF\x08\xb8w\xe3\x17'
    b'\xb3\xf5-?\ro\xa56\xb37{\xe8\x7f@\x0f\x10\xc4?\x05>\xd7"\x84\xac\xb7\xc3\xe3w\x91\x1e'
    b'!\xb1\xf8\x80=]\xa5\x939$\xc1\x8f\xdeY\xb4\x8aS5\xc3%+\xb3\xcb\xf1\x12\x84\t\x16\xdc\xbb'
    b'%\x1e\x06\xac\x98\xa2V\x11\x11\xed\xa2\xc8\x1aC\xb3\x8cE\rX\xd0\x13\xe6\x10pM\xab\x87\xb1\xe9\xd7'
    b'@\xf9UK\x85\x1a\xebC\x15\x8a\xdc\xf3\xb6\x07S\\\x08\xe0\xb0\x00\xd1"&\xee\x15F%\xb6\x00\x01'
    b'\xd8\x06\xa5\x19\x00\x00\xf7\xce:\xdb\xb1\xc4g\xfb\x02\x00\x00\x00\x00\x04YZ'
))
del __deserialize
from .util import bind_nodes as __bind_nodes
__bind_nodes(DEFAULT_GRAMMAR)
del __bind_nodes

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
