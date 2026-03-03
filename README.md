#  Mini Python Compiler

A full-featured **Mini Python Compiler & Interpreter** built from scratch in Python — covering the entire W3Schools Python tutorial feature set. Designed as a portfolio project demonstrating compiler fundamentals: lexical analysis, parsing, AST construction, semantic analysis, and tree-walking interpretation.

---

##  Quick Start

```bash
# Install dependency
pip install streamlit

# Run the interactive demo
streamlit run src/demo.py

# Or run a script directly
python src/interpreter.py examples/full_demo.py

# Run tests
python -m pytest tests/ -v
```

---

##  Compiler Pipeline

```
Source Code
    │
    ▼
┌─────────────┐
│   Lexer     │  → Token stream (lexer.py)
│             │    Handles: keywords, operators, literals, indentation,
│             │    strings, comments, line/col tracking
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Parser    │  → Abstract Syntax Tree (parser.py + ast_nodes.py)
│             │    Recursive descent, full expression grammar,
│             │    operator precedence, all statement types
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Semantic   │  → Symbol table, scope analysis (semantic.py)
│  Analyzer   │    Undefined var/fn detection, redeclaration warnings,
│             │    return/break/continue placement checks
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Interpreter │  → Execution output (interpreter.py)
│             │    Tree-walking, scoped environments, built-ins,
│             │    execution history for visualization
└─────────────┘
```

---

##  Project Structure

```
mini_python_compiler/
├── src/
│   ├── lexer.py        # Tokenizer — handles all Python tokens
│   ├── parser.py       # Recursive-descent parser
│   ├── ast_nodes.py    # 50+ AST node classes
│   ├── semantic.py     # Semantic analysis & symbol table
│   ├── interpreter.py  # Tree-walking interpreter
│   ├── errors.py       # Custom error hierarchy
│   └── demo.py         # Streamlit interactive demo
├── examples/
│   └── full_demo.py    # Full feature showcase
├── tests/
│   └── test_compiler.py  # 100+ unit tests
├── requirements.txt
└── README.md
```

---

##  Supported Language Features

| Category | Features |
|---|---|
| **Variables** | Assignment, type hints (`x: int = 5`), augmented (`+=`, `-=`…), tuple unpacking |
| **Data Types** | int, float, str, bool, None |
| **Numbers** | int, float, hex, oct, binary literals, arithmetic, bitwise |
| **Casting** | `int()`, `float()`, `str()`, `bool()` |
| **Strings** | Indexing, slicing, `.upper()`, `.lower()`, `.replace()`, `.split()`, `.join()`, `.strip()`, f-strings |
| **Booleans** | `True`, `False`, `and`, `or`, `not`, truthiness |
| **Operators** | All arithmetic, comparison, logical, bitwise, membership (`in`, `not in`), identity (`is`) |
| **Lists** | Literals, `.append()`, `.insert()`, `.remove()`, `.sort()`, `.pop()`, slicing, comprehensions |
| **Tuples** | Literals, unpacking, slicing, `.count()`, `.index()` |
| **Sets** | Literals, `.add()`, `.discard()`, union, intersection, difference, comprehensions |
| **Dictionaries** | Literals, CRUD, `.keys()`, `.values()`, `.items()`, `.get()`, `.pop()`, comprehensions |
| **If/Else** | `if`, `elif`, `else`, ternary operator |
| **Match** | `match`/`case` with literals, capture variables, wildcard `_`, guard `if` |
| **While** | `while`, `break`, `continue`, `else` clause |
| **For** | `for`/`in`, `range()`, tuple unpacking, `break`, `continue`, `else` clause |
| **Functions** | `def`, parameters, defaults, type hints, `return`, recursion, closures, `global` |
| **Range** | `range(stop)`, `range(start, stop)`, `range(start, stop, step)` |
| **Arrays** | Lists used as arrays, 2D arrays via list comprehensions |
| **Iterators** | `iter()`, `next()`, `enumerate()`, `zip()`, `map()`, `filter()`, `reversed()` |
| **Lambda** | `lambda`, higher-order functions |
| **Classes** | `class`, `__init__`, methods, attributes, inheritance |
| **Comprehensions** | List, dict, set comprehensions with optional `if` filter |
| **Exceptions** | `try`, `except`, `else`, `finally`, `raise`, `assert` |
| **Import** | `import`, `from … import` (delegates to Python's importlib) |
| **Built-ins** | 40+ built-in functions |

---

##  Interactive Demo

The Streamlit demo (`src/demo.py`) provides:

- **Code Editor** — syntax-highlighted Monaco-like textarea with 20 pre-built examples
- **Output Panel** — live execution results
- **AST Viewer** — tree visualization of the parsed program
- **Symbol Table** — all variables, functions, and classes after execution
- **Execution History** — step-by-step scope snapshots
- **Token Stream** — raw token output (toggle in sidebar)

---

##  Testing

```bash
python -m pytest tests/test_compiler.py -v
```

The test suite covers:
- Lexer: integers, floats, strings, keywords, operators, comments, line tracking
- Parser: all statement types, operator precedence, complex expressions
- Semantic: undefined variables, function redeclaration warnings, misplaced return/break/continue
- Interpreter: 100+ execution tests spanning all language features

---

##  Design Decisions

- **No regex for parsing** — pure recursive descent for clarity and control
- **Indentation via INDENT/DEDENT tokens** — matches CPython's approach
- **Semantic errors are warnings by default** — interpreter runs anyway (toggle strict mode in demo)
- **Delegates imports to Python** — `import math` works by calling Python's `importlib`
- **f-strings simplified** — treated as regular strings in this version
- **Performance note** — designed for small scripts; large recursive programs may be slow due to AST tree-walking

---

##  Demo Screenshot

Run `streamlit run src/demo.py` and open `http://localhost:8501` to see:

```
┌─────────────────────────────────────────────────────────────┐
│   Mini Python Compiler — Interactive Demo                  │
├─────────────────────────────┬───────────────────────────────┤
│  Code Editor                │   Output                    │
│  ─────────────────────────  │  ──────────────────────────── │
│  def factorial(n):          │  3628800                      │
│      if n <= 1:             │                               │
│          return 1           │   AST                       │
│      return n*factorial(n-1)│  ──────────────────────────── │
│  print(factorial(10))       │  Program(2 statements)        │
│                             │  ├─ FunctionDef(factorial)    │
│                             │  └─ Print(...)                │
│                             │                               │
│                             │   Symbol Table              │
│                             │  factorial │ fn │ line 1      │
└─────────────────────────────┴───────────────────────────────┘
```
