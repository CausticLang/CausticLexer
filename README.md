# Important note
**This is now unused in favor of instead utilizing a more mature pre-existing
parsing framework**

Later in development of Caustic, this may or may not be revisited

# Caustic's lexing/grammar framework

The `basic_compiler` module is a less advanced compiler, but is used to
bootstrap the `Compiler`

The `Compiler` class compiles grammars from Caustic grammar (`.cag`) files into nodes,
and uses a grammer system built in Caustic grammar format and compiled with the `basic_compiler` module

The `Compiler` is loaded through the `load_compiler()` function in the package,
and can be cached to the disk using the `save_compiler()` function

The `nodes` module provides the nodes themselves, and allows manually building grammar by
supplying nodes

The `serialize` module provides functions for serializing and deserializing nodes

The `util` module provides small utilities

# The `.cag` specification

## Pragmas
Pragmas are special directives embedded in the grammar  
These are only supported on the bootstrapped `compile` module

### Include
> `$include [path]`

Allows putting multiple grammar files together

Relative paths provided as `[path]` will be checked against the following
directories, in order:
- The path of the includer/importer (if possible)
- The `builtin_path` of the `compiler` module (the location of `compiler.py`)
- The current directory

## Comments
Comments may start with a `#`

## Statements
A statement begins with an [identifier](#identifier), followed by an `=`,
then an [expression](#expression), and finally a `;`

### Identifier
An identifier is a sequence of alphanumeric characters, underscores, and periods

Note: `basic_compiler` will not accept identifiers with periods

## Expression
Expressions consist of nodes, where a node can be as simple as a [string](#string) to as complex as a [group](#group)

### Naming
> `nodes.Node.name`

Named nodes are denoted by a name (alphanumeric, underscores, and periods), followed
by a `:`, and then the node/expression  
This controls the return value of containing groups

Note: `basic_compiler` will not accept node names with periods

#### Anonymous
"Anonymous" named nodes are expressions prefixed with `:`, but with
no leading name

#### Unpack
"Unpack" nodes are expressions prefixed with `^:`

Note: `basic_compiler` will not accept unpack nodes

### Group
> `nodes.NodeGroup`

The top level of an expression is implicitly grouped

A simple group node is opened by `(` and closed by `)`  
Groups match the nodes inside of them in a sequence in order  
The return value of this group will be dependent on its contents' [naming](#naming):

- A group containing no named nodes will return a list of its nodes' results
- A group containing nodes with "[anonymous](#anonymous)" names returns the last matched anonymous nodes' return value
- A group containing [named](#naming) nodes returns a dict containing a mapping of the names to the nodes' results
- Any [unpack](#unpack) nodes will unpack either their elements (sequence) or their names and values into the surrounding group's result

Mixing anonymous and named expressions in a single group will result in an error

#### Whitespace sensitive group
> `nodes.NodeGroup`, `keep_whitespace=True`

A whitespace sensitive group is opened by `{` and closed by `}`  
The only difference between this type of group and a normal group is that it does not implicitly
discard whitespace between its nodes

#### Union
> `nodes.UnionNode`

A union is opened by `[` and closed by `]`  
Unions match any of their contained nodes

#### Range
> `nodes.NodeRange`

Can be created in the following ways:
- ` - [node]`: Matches any amount of `[node]`
- ` x- [node]`: Matches `x` or more of `[node]`
- ` -x [node]`: Matches up to (but not including) `x` of `[node]`
- ` a-b [node]`: Matches between `a` (inclusive) and `b` (exclusive) of `[node]`

Note that this should be placed *after* a (name)[#naming]

### Real
Real nodes are nodes that actually match content, such as strings or patterns

#### String
> `nodes.StringNode`

The simplest node, denoted either by single quotes (`''`) or double quotes (`""`)  
Supports escape characters

> Note: despite the name of this node, it is important to remember that the nodes only match bytes!

#### Pattern
> `nodes.PatternNode`

Matches a regular expression, denoted by slashes (`/`) in the following syntax:  
> [target group](#target-group) `/` pattern `/` [flags](#flags)

##### Target Group
In a pattern, if a target group is given (as an integer), the result of this
node will be the bytes of that group instead of the entire match

##### Flags
Supports these common RegEx flags:
- `i`: ignore case / case insensitive
- `m`: multiline - `^` matches beginning of line or string, `$` matches end of either
- `s`: single-line / "dotall" - `.` matches newlines as well

### Meta
"Meta" nodes that don't actually match anything, but can change some context

#### Stealer
> `nodes.Stealer`

A "stealer" node is denoted by a `!`, and is only acceptable in a group

If a [group](#group) reaches a "stealer" node, then the group will raise an exception
if any of the subsequent nodes fail

#### Context
> `nodes.Context`

A context is created with an opening `<` and closing `>`  
Context nodes always mach, with the result being the (string) contents

Context nodes should contain either a [string](#string),
or a short sequence of alphanumeric characters and underscores

#### Node Reference
> `nodes.NodeRef`

Denoted by an `@`, followed by a node name (as a string of alphanumeric characters, underscores, and periods)

Matches the value of the targeted node, and returns the result of that

Must be bound using either its `.bind()` method, or automatically through the
default compilers

Note: `basic_compiler` will not accept node references with periods


# Changelog

## 0.2.0
- Implemented node saving and loading through the `serialize` module
- Moved `compiler.bind_nodes()` to `util.bind_nodes()`

## 1.0.0
- Completely reworked compiler caching
- Removed `$import` pragma
- Moved `WHITESPACE_PATT` to `.util`
- Changed `nodes.Node.NO_RETURN` to singleton(ish) `util.NO_MATCH`

### 1.0.0-1
- Fixed an inaccuracy in README

## 1.0.1
- Added builtin `grammar.cag` to package
- Added precompiled `precompiled_nodes.pkl` to package

## 1.0.2
- Fixed error causted by `compiler.py` `Compiler.compile_buffermatcher()` passing unneeded kwarg to `.pre_process()`
- Made `NodeSyntaxError` self-formatting also include exception notes

## 1.1.0
- Added support for periods in node names
- Fixed `Compiler.post_process_compile()` not actually doing anything

## 1.2.0
- Implemented [unpacking](#unpack) nodes

## 1.2.1
- Fixed several nodes improperly stripping whitespace

## 1.2.2
- Fixed unpacking never triggering
- Fixed `NodeRange`s raising exceptions upon backtracking
