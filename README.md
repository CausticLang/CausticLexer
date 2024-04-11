Caustic's lexing/grammar framework

The `compile` module allows compilation of Caustic grammar files (`.cag`, see below)
into nodes

The `nodes` module provides the nodes themselves, and allows manually building grammar by
supplying nodes

# The `.cag` specification

## Comments
Comments may start with a `#`

## Statements
A statement begins with an [identifier](#identifier), followed by an `=`,
then an [expression](#expression), and finally a `;`

### Identifier
An identifier is a sequence of alphanumeric characters and underscores

## Expression
Expressions consist of nodes, where a node can be as simple as a [string](#string) to as complex as a [group](#group)

### Naming
> `nodes.Node.name`

Named nodes are denoted by a name (alphanumeric and underscores), followed
by a `:`, and then the node/expression  
This controls the return value of containing groups

#### Anonymous
"Anonymous" named nodes are expressions prefixed with `:`, but with
no leading name

### Group
> `nodes.NodeGroup`

The top level of an expression is implicitly grouped

A simple group node is opened by `(` and closed by `)`  
Groups match the nodes inside of them in a sequence in order  
The return value of this group will be dependent on its contents' [naming](#naming):

- A group containing no named nodes will return a list of its nodes' results
- A group containing nodes with "[anonymous](#anonymous)" names returns the last matched anonymous nodes' return value
- A group containing [named](#naming) nodes returns a dict containing a mapping of the names to the nodes' results

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
