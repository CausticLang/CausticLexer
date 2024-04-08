#!/bin/python3

#> Imports
import io
import sys
import json
import click
import pickle
import typing
import tomllib
import pickletools
from pathlib import Path

import lib
#</Imports

#> Header
SUFFIXES = {
    'grammar': '.cag.toml',
    'patterns': '.cap.toml',
    'nodes': '.can.toml',
    'pickled': '.cag.pkl',
    'json': '.cag.json',
}

PICKLE_VERSION = pickle.HIGHEST_PROTOCOL

class GrammarUnpickler(pickle.Unpickler):
    __slots__ = ()

    ALLOWED_CLASSES = {
        're': {'Pattern', '_compile'},
        'lib.nodes.flat': set(lib.nodes.flat.__all__),
        'lib.nodes.nested': set(lib.nodes.nested.__all__),
        'lib.nodes.meta': set(lib.nodes.meta.__all__),
        'lib.loaders.pattern': {'PatternLoader',},
    }

    def find_class(self, module: str, name: str) -> type:
        if (m := self.ALLOWED_CLASSES.get(module, None)) is not None:
            if name in m: return super().find_class(module, name)
            raise pickle.UnpicklingError(f'Name {name!r} is not allowed under module {module!r}--'
                                          'pickled file may be corrupted or malicious')
        raise pickle.UnpicklingError(f'Module {module!r} is not allowed--'
                                     'pickled file may be corrupted or malicious')

def node_key_from_type(type_: type[lib.nodes.GrammarNode]) -> str:
    # Attempts to recover a node's type-key from its type
    for k,t in lib.loaders.nodes.NODE_KEYS.items():
        if t is type_: return k
    raise TypeError(f'Type {type_} has no node key')

def load_files(files: tuple[typing.BinaryIO, ...], *, filetype_default: typing.Literal[*SUFFIXES.keys()],
               filetype_force: typing.Literal[*SUFFIXES.keys()] | None) -> lib.Grammar:
    # Attempts to load a grammar, nodes, or patterns from files
    gram = lib.Grammar()
    for file in files:
        if filetype_force is None:
            for k,s in SUFFIXES.items():
                if file.name.endswith(s):
                    mode = k
                    break
            else:
                click.echo(f'Warning: unknown file type {file.name!r}--using default', file=sys.stderr)
                mode = filetype_default
        else: mode = filetype_force
        click.echo(f'Parsing {file.name!r} as {mode!r}', file=sys.stderr)
        match mode:
            case 'patterns':
                gram.patterns.load(file)
            case 'nodes':
                for _,node in lib.loaders.nodes.load(file):
                    gram.add_node(node, replace=True, bind=False, compile=False)
            case 'pickled':
                data = GrammarUnpickler(file).load()
                gram.patterns.multiadd(data.get('patterns', {}), replace=False)
                for node in data.get('nodes', ()):
                    gram.add_node(node, replace=True, bind=False, compile=False)
            case 'grammar' | 'json':
                data = (tomllib if mode == 'grammar' else json).load(file)
                patts = data.get('patterns', ())
                gram.patterns.multiadd(dict(zip(patts.keys(), map(str.encode, patts.values()))))
                for _,node in lib.loaders.nodes.load_dict(data.get('nodes', {})):
                    gram.add_node(node, replace=True, bind=False, compile=False)
    return gram
#</Header

#> Main >/
cli = click.Group()

@cli.command
@click.argument('targets', type=click.File('rb'), nargs=-1)
@click.option('--output', type=click.File('wb'), help='The file to write to (defaults to stdout)', default='-')
@click.option('--format', type=click.Choice(('pickle_optimized', 'pickle', 'json_pretty', 'json', 'json_min')), default='pickle_optimized',
              help='The format to write as')
@click.option('--default-filetype', type=click.Choice(tuple(SUFFIXES.keys())),
              help='Read all files with unknown suffixes as this type', default='grammar')
@click.option('--force-filetype', type=click.Choice(tuple(SUFFIXES.keys())), help='Force all files to be read as this type', default=None)
def compile(*, targets: tuple[typing.BinaryIO, ...], output: typing.BinaryIO | None,
            format: typing.Literal['pickle_optimized', 'pickle', 'json_pretty', 'json', 'json_min'],
            default_filetype: typing.Literal[*SUFFIXES.keys()], force_filetype: typing.Literal[*SUFFIXES.keys()] | None) -> None:
    '''
        Joins all of the targets into one

        Can either join them into a single JSON file, when format is "json_pretty", "json", or "json_min",
            or preprocess and create nodes and then pickle those and the patterns
    '''
    gram = load_files(targets, filetype_default=default_filetype, filetype_force=force_filetype)
    if format.startswith('pickle'):
        comp = pickle.dumps({'patterns': gram.patterns.patterns, 'nodes': tuple(gram.nodes.values())}, protocol=PICKLE_VERSION)
        click.echo(f'Compiled into pickle of {len(comp)} byte(s)', file=sys.stderr)
        if format == 'pickle_optimized':
            click.echo(f'Optimized {len(comp)} into '
                       f'{len(comp := pickletools.optimize(comp))} byte(s)', file=sys.stderr)
    else:
        comp = (json.dumps({'patterns': dict(zip(gram.patterns.patterns.keys(), map(bytes.decode, gram.patterns.patterns.values()))),
                            'nodes': tuple({'type': node_key_from_type(type(n)), **n.args}
                                           for _,n in gram.nodes.items())},
                           separators=((',', ':') if (format == 'json_min') else json.dumps.__kwdefaults__['separators']),
                           indent=(4 if format == 'json_pretty' else json.dumps.__kwdefaults__['indent']))).encode()
    click.echo(f'Compiled to {len(comp)} byte(s)', file=sys.stderr)
    output.write(comp)
    click.echo(f'Wrote compiled file to {output.name}', file=sys.stderr)

if __name__ == '__main__': cli()
