# Thirsty-Lang Grammar (Tier 1)

**Edition:** Thirsty-Lang v0.8.6

**Scope:** syntax accepted by `utf.thirsty_lang.lexer.Lexer` and
`utf.thirsty_lang.parser.Parser`

**Canonical handbook:** [Thirsty-Lang 101](THIRSTY_LANG_101.md)

This is the source-authoritative EBNF-style reference for the Tier 1 parser.
It describes accepted syntax, not every semantic or governance guarantee. The
lexer, parser, and their regression tests govern if an older example conflicts
with this document.

Several words used by higher tiers are reserved by the Tier 1 lexer. Some also
have a Tier 1 parse form: `shield` and `detect` wrap a block; `sanitize` and
`armor` wrap an expression; `morph` declares a callable transform; and `defend`
records a strategy form. Their presence alone does not provide a higher-tier
security guarantee. See the [governance model](governance_model.md).

---

## Notation

- `"..."` denotes a literal keyword or symbol.
- `( ... )` groups grammar terms.
- `[ ... ]` is optional.
- `{ ... }` repeats zero or more times.
- `A | B` is alternation.
- `/* ... */` is a note about parsing or semantics.

---

## 1. Lexical grammar

### 1.1 Identifiers and member access

```ebnf
identifier_start = alphabetic | "_" ;
identifier_rest  = alphanumeric | "_" ;
identifier       = identifier_start { identifier_rest } ;

member_access    = expression "." member_name ;
```

`alphabetic` and `alphanumeric` follow Python's Unicode-aware `str.isalpha()`
and `str.isalnum()` behavior. A dot is **not** part of an identifier. For
example, `user.role` lexes as `identifier`, `.`, `identifier` and the parser
builds a member-access path. After a dot, a reserved word whose spelling is a
valid identifier may be used as the member name, such as `log.error`.

### 1.2 Numbers

```ebnf
digit          = "0".."9" ;
hex_digit      = digit | "a".."f" | "A".."F" ;
oct_digit      = "0".."7" ;
binary_digit   = "0" | "1" ;

decimal_int    = digit { digit } ;
hex_int        = ( "0x" | "0X" ) hex_digit { hex_digit } ;
octal_int      = ( "0o" | "0O" ) oct_digit { oct_digit } ;
binary_int     = ( "0b" | "0B" ) binary_digit { binary_digit } ;
integer        = decimal_int | hex_int | octal_int | binary_int ;

exponent       = ( "e" | "E" ) [ "+" | "-" ] digit { digit } ;
float          = decimal_int "." digit { digit } [ exponent ]
               | decimal_int exponent ;
```

`3.` is an integer followed by a dot, not a float. A fractional form therefore
requires at least one digit after the dot.

### 1.3 Strings and escapes

```ebnf
string         = double_quoted_string | single_quoted_string ;
double_quoted_string = '"' { string_character | escape } '"' ;
single_quoted_string = "'" { string_character | escape } "'" ;

escape         = "\\n" | "\\t" | "\\0" | "\\\\" | "\\\"" | "\\'" ;
```

The decoded escapes in v0.8.6 are newline (`\n`), tab (`\t`), NUL (`\0`),
backslash (`\\`), double quote (`\"`), and single quote (`\'`). `\r` and
hex escapes such as `\x41` are not implemented escape forms. For compatibility,
the current lexer drops the backslash from an unknown escape and retains the
following character; code should not rely on that fallback. Quoted strings may
span physical lines.

### 1.4 Comments and whitespace

```ebnf
line_comment   = "//" { character - newline } ( newline | EOF ) ;
block_comment  = "/*" { character | block_comment } "*/" ;
whitespace     = " " | "\t" | "\r" | "\n" ;
```

Block comments may nest. Whitespace, including newlines, separates tokens but
does not itself produce a statement-termination token.

---

## 2. Program structure and types

```ebnf
program        = [ module_header ] { statement } EOF ;

module_header  = "module" identifier ":" module_mode ;
module_mode    = "core" | "governed" | "strict" | "pure" ;

import_stmt    = "import" string [ "as" identifier ] [ ";" ] ;

type_name      = identifier ;
parameter      = identifier [ ":" type_name ] ;
parameters     = "(" [ parameter { "," parameter } ] ")" ;
```

The module header, when present, must be first. Imports are ordinary statements
and may occur wherever the parser accepts a statement.

Type annotations currently consume exactly one identifier. The checker
recognizes the built-in names `Int`, `Float`, `Bool`, `String`, `Void`, `Any`,
and `Error`. Function-type, tuple-type, and bracketed generic syntax are not
accepted in a Tier 1 annotation by the v0.8.6 parser.

In `strict` mode, `drink` and `let` bindings require an initializer at runtime.
In `pure` mode, side-effecting `pour` and `sip` operations are rejected at
runtime.

---

## 3. Expressions

The productions below are ordered from lowest to highest binding power.

```ebnf
expression       = assignment ;

assignment       = low_pipe [ "=" assignment ] ;

low_pipe         = logical_or { ( "|" | "|>" ) logical_or } ;

logical_or       = logical_and { "or" logical_and } ;
logical_and      = logical_not { "and" logical_not } ;
logical_not      = { "not" } comparison ;

comparison       = additive
                   { ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) additive } ;

additive         = multiplicative { ( "+" | "-" ) multiplicative } ;
multiplicative   = high_combine { ( "*" | "/" | "%" ) high_combine } ;

high_combine     = numeric_unary { ( "->" | "||" | "^" ) numeric_unary } ;
numeric_unary    = "-" numeric_unary | postfix ;

postfix          = primary
                   { call_suffix | subscript_suffix | member_suffix } ;
call_suffix      = "(" [ argument_list ] ")" ;
subscript_suffix = "[" expression "]" ;
member_suffix    = "." member_name ;
argument_list    = expression { "," expression } ;

primary          = literal
                 | identifier
                 | "this"
                 | "(" expression ")"
                 | array_literal
                 | lambda_expression
                 | guard_expression
                 | quenched_expression
                 | flow_expression
                 | new_expression
                 | cascade_expression ;

literal          = integer | float | string | "true" | "false" | "none" ;
array_literal    = "[" [ argument_list ] "]" ;

lambda_expression = "glass" parameters [ "->" type_name ] block ;

guard_expression  = "thirst" expression "quench" expression ;
quenched_expression = "quenched" [ "(" [ expression ] ")" ] ;

flow_expression   = ( "flood" | "drip" | "evaporate" | "condense"
                    | "sanitize" | "armor" ) expression ;

new_expression    = "new" identifier [ "(" [ argument_list ] ")" ] ;
cascade_expression = "cascade" expression ;
```

`member_name` is an identifier-shaped token; it may be a reserved word after
the dot. Method calls use the same postfix chain as ordinary calls, for example
`object.method(arg)[0]`.

There is no unary `+` operator. Logical negation is spelled `not`; a bare `!`
is a lexer error, while `!=` is the supported inequality operator. Adjacent
string literals are not an implicit concatenation form, and the parser does
not implement the formerly documented `identifier { field = value }` struct
literal.

### Exact precedence and associativity

| Binding power | Operators/forms | Associativity |
|---:|---|---|
| 1 (lowest) | assignment `=` | right |
| 2 | low pipe `|`, `|>` | left |
| 3 | `or` | left |
| 4 | `and` | left |
| between 4 and 5 | prefix `not` | right/prefix |
| 5 | `==`, `!=`, `<`, `>`, `<=`, `>=` | left, one shared level |
| 6 | `+`, `-` | left |
| 7 | `*`, `/`, `%` | left |
| 8 | `->`, `||`, `^` | left |
| prefix at 8 | unary `-` | right/prefix |
| 9 (highest operators) | call `()`, member `.`, subscript `[]` | left/postfix |

This table mirrors `Parser._precedence_map()`. In particular, equality and
ordering comparisons share a level, `and` binds more tightly than `or`, and
`not a == b` means `not (a == b)`.

---

## 4. Statements and blocks

```ebnf
statement        = variable_decl
                 | for_stmt
                 | pour_stmt
                 | sip_stmt
                 | if_stmt
                 | refill_stmt
                 | times_stmt
                 | return_stmt
                 | import_stmt
                 | block
                 | function_decl
                 | fountain_decl
                 | spillage_stmt
                 | cleanup_stmt
                 | throw_stmt
                 | security_block
                 | morph_decl
                 | defend_decl
                 | enum_decl
                 | struct_decl
                 | interface_decl
                 | mutation_decl
                 | symbol_stmt
                 | pipe_block_stmt
                 | expression_stmt ;

block            = "{" { statement } "}" ;

variable_decl    = "drink" [ "mut" ] identifier
                   [ ":" type_name ] [ "=" expression ] [ ";" ]
                 | "let" identifier
                   [ ":" type_name ] [ "=" expression ] [ ";" ]
                 | identifier ":=" expression [ ";" ] ;

for_stmt         = "for" identifier "in" expression block
                 | "for" "(" identifier "in" expression ")" block ;

pour_stmt        = "pour" expression [ ";" ] ;
sip_stmt         = "sip" expression [ ";" ] ;

if_stmt          = "thirsty" "(" expression ")" block
                   [ "hydrated" ( if_stmt | block ) ] ;

refill_stmt      = "refill" "(" identifier "in" expression ")" block
                 | "refill" "(" expression ")" block
                 | c_style_refill ;

c_style_refill   = "refill" "(" c_style_init expression ";" expression ")" block ;
c_style_init     = declaration_init | expression ";" ;
declaration_init = ( "drink" [ "mut" ] identifier
                   | "let" identifier )
                   [ ":" type_name ] [ "=" expression ] [ ";" ] ;

times_stmt       = "times" expression block ;
return_stmt      = "return" [ expression ] [ ";" ] ;
throw_stmt       = "throw" expression [ ";" ] ;

pipe_block_stmt  = ( "|" | "|>" ) expression ";" ;
expression_stmt  = expression [ ";" ] ;
```

Most statement forms accept, but do not require, a trailing semicolon. There is
no automatic semicolon insertion because newlines are discarded by the lexer;
the parser instead recognizes the end of an expression or declaration from the
following token. Empty `;` is not a statement.

Semicolons remain required in two places:

1. the condition separator in a C-style `refill` and the first separator when
   its initializer is an expression; and
2. the terminator of a statement-level pipe block.

A `drink` or `let` initializer selects the C-style `refill` form directly, so
its first separator is optional in the current parser. The canonical spelling
still includes both separators: `refill (drink i = 0; i < 3; i = i + 1) { ... }`.

One dispatch edge is also part of the v0.8.6 behavior: a statement beginning
with `sanitize`, `armor`, `cascade`, or `new` bypasses the generic expression-
statement parser. A trailing semicolon is therefore not consumed and would be
read as an invalid empty statement; omit it on those four direct forms.

---

## 5. Declarations and governed forms

### 5.1 Functions and contracts

```ebnf
function_decl    = "glass" identifier parameters [ "->" type_name ]
                   { contract_clause } block ;

contract_clause  = "requires" expression
                 | "ensures" expression
                 | "invariant" expression ;
```

Named and anonymous functions use `->` for return annotations. The formerly
documented `: type` return form is not accepted. Contract clauses may appear in
any order; canonical code uses each kind at most once.

A function with a `requires`, `ensures`, or `invariant` clause is a governed
function. In governed mode its contracts are evaluated on every call, and
entry also requires the configured T.A.R.L. policy and authority path. See
[Runtime Enforcement](governance_model.md#runtime-enforcement).

### 5.2 Fountains

```ebnf
fountain_decl    = "fountain" identifier "{" { fountain_member } "}" ;

fountain_member  = function_decl
                 | "drink" [ "mut" ] fountain_field [ ";" ]
                 | fountain_field [ ";" ] ;

fountain_field   = identifier [ ":" type_name ] [ "=" expression ] ;
```

Fountain inheritance, mixin lists, and interface lists after the fountain name
are not supported by the v0.8.6 parser. A constructor is an ordinary method
named `init`, written `glass init(...) { ... }`.

### 5.3 Error handling and cleanup

```ebnf
spillage_stmt    = "spillage" block
                   { "error" [ "(" identifier ")" ] block } ;

cleanup_stmt     = "cleanup" block "finally" block ;
```

The optional identifier in an `error(name)` handler receives the thrown value.

### 5.4 Data and interface declarations

```ebnf
enum_decl        = "enum" identifier
                   "{" [ identifier { "," identifier } ] "}" ;

struct_decl      = "struct" identifier "{" { struct_field [ ";" ] } "}" ;
struct_field     = identifier [ ":" type_name ] ;

interface_decl   = "interface" identifier
                   "{" { interface_signature [ ";" ] } "}" ;
interface_signature = identifier parameters [ "->" type_name ] ;
```

Enum variants are names only; payload-bearing variants are not supported.
Interface signatures contain named parameters (with optional type annotations),
an optional `->` return type, and no body. The Tier 1 parser does not support
interface inheritance or an `implements` clause on fountains; this syntax does
not claim either feature.

### 5.5 Higher-tier marker forms accepted by Tier 1

```ebnf
morph_decl       = "morph" identifier parameters block ;

security_block   = ( "shield" | "detect" ) block ;

defend_decl      = "defend" identifier [ "(" identifier ")" ]
                   "{" { expression [ ";" ] } "}" ;

mutation_decl    = "mutation" identifier "{"
                     "validated_canonical" "{"
                       { mutation_section }
                     "}"
                   "}" ;

mutation_section = "shadow" block
                 | "invariant" block
                 | "canonical" block ;

symbol_stmt      = "symbol" identifier [ ";" ] ;
```

`morph` has parameters and a body but no return annotation. `shield` and
`detect` take a block directly; neither accepts a parenthesized condition.

---

## 6. Lexically reserved words

```text
drink, let, for, strict, pure,
pour, sip, thirsty, hydrated, thirst, quench, refill, times,
glass, reservoir, well, of, flood, drip, evaporate, condense, fountain,
return, parched, quenched, empty, mut, in, import, from, as,
shield, sanitize, armor, morph, detect, defend, cascade, this, new,
public, private, await, spillage, cleanup, finally, error, throw,
policy, when, allow, deny, escalate, mutation, validated_canonical,
invariant, shadow, canonical, promote, reject, governed, requires, ensures,
enum, struct, interface, symbol, module, core, and, or, not,
true, false, none
```

This is the complete v0.8.6 `KEYWORDS` set. Reservation does not mean that each
word starts a Tier 1 parser production. Some tokens exist for higher-tier and
forward-compatibility work.

---

## 7. Source anchors

The implementation points that define this edition are:

- `src/utf/thirsty_lang/lexer.py` - token boundaries, number and string forms,
  comments, and escape decoding;
- `src/utf/thirsty_lang/token.py` - token kinds and reserved words;
- `src/utf/thirsty_lang/parser.py` - statements, declarations, expressions,
  precedence, and associativity;
- `tests/test_lexer.py`, `tests/test_parser_coverage.py`, and
  `tests/test_parser_precedence.py` - executable grammar regressions.
