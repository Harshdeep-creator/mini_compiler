"""
Tabs:
  1. Code Editor + Output
  2. AST Viewer
  3. Symbol Table
  4. Execution History
  5. Token Stream
"""

import sys
import os
import io
import json

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from lexer import tokenize, LexerError
from parser import Parser, ParseError
from semantic import SemanticAnalyzer
from interpreter import Interpreter
from errors import RuntimeError_

# ─── page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Mini Python Compiler",
    page_icon="🐍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
  .stTextArea textarea { font-family: 'Fira Code', monospace; font-size: 14px; }
  .output-box { background: #1e1e1e; color: #d4d4d4; padding: 1rem;
                border-radius: 8px; font-family: monospace; white-space: pre-wrap; min-height: 80px; }
  .error-box  { background: #3a0000; color: #ff6b6b; padding: 1rem;
                border-radius: 8px; font-family: monospace; white-space: pre-wrap; }
  .warn-box   { background: #2a2000; color: #ffd700; padding: 0.5rem 1rem;
                border-radius: 8px; font-family: monospace; white-space: pre-wrap; }
  .ast-box    { background: #0d1117; color: #58a6ff; padding: 1rem;
                border-radius: 8px; font-family: monospace; white-space: pre; overflow-x: auto; }
  .sym-row    { font-family: monospace; }
  .badge      { display:inline-block; padding:2px 8px; border-radius:4px;
                font-size:12px; font-weight:bold; margin-left:6px; }
  .badge-var  { background:#1a3a1a; color:#4caf50; }
  .badge-fn   { background:#1a2a3a; color:#64b5f6; }
  .badge-cls  { background:#3a1a3a; color:#ce93d8; }
  .badge-mod  { background:#3a2a1a; color:#ffb74d; }
</style>
""", unsafe_allow_html=True)

# ─── sidebar – example programs ──────────────────────────────────────────────

EXAMPLES = {
    "Hello World": 'print("Hello, World!")',

    "Variables & Types": """\
x: int = 42
y: float = 3.14
name: str = "Alice"
flag: bool = True
print(x, y, name, flag)
print(type(x), type(y))
""",

    "Arithmetic": """\
a = 10
b = 3
print(a + b)   # 13
print(a - b)   # 7
print(a * b)   # 30
print(a / b)   # 3.333...
print(a // b)  # 3
print(a % b)   # 1
print(a ** b)  # 1000
""",

    "Strings": """\
s = "Hello, Python!"
print(len(s))
print(s.upper())
print(s.lower())
print(s[0:5])
print(s.replace("Python", "World"))
print(s.split(", "))
words = ["Hello", "World"]
print(" ".join(words))
""",

    "Booleans": """\
x = True
y = False
print(x and y)
print(x or y)
print(not x)
print(bool(0), bool(1), bool(""), bool("hi"))
""",

    "If / Elif / Else": """\
score = 85
if score >= 90:
    print("A")
elif score >= 80:
    print("B")
elif score >= 70:
    print("C")
else:
    print("F")
""",

    "While Loop": """\
i = 1
while i <= 5:
    print(i)
    i += 1
print("Done!")
""",

    "For Loop + Range": """\
for i in range(1, 6):
    print(i)

total = 0
for n in range(1, 101):
    total += n
print("Sum 1-100:", total)
""",

    "Lists": """\
fruits = ["apple", "banana", "cherry"]
print(fruits)
fruits.append("date")
fruits.insert(1, "blueberry")
fruits.remove("banana")
print(fruits)
print(len(fruits))
print(fruits[0], fruits[-1])
fruits.sort()
print(fruits)
print("cherry" in fruits)
""",

    "Tuples": """\
coords = (10, 20)
x, y = coords
print(x, y)
t = (1, 2, 3, 4, 5)
print(t[1:4])
print(len(t))
print(t.count(2))
print(t.index(3))
""",

    "Sets": """\
s = {1, 2, 3, 4, 5}
s.add(6)
s.discard(3)
print(s)
a = {1, 2, 3}
b = {3, 4, 5}
print(a | b)   # union
print(a & b)   # intersection
print(a - b)   # difference
print(a ^ b)   # symmetric difference
""",

    "Dictionaries": """\
person = {"name": "Alice", "age": 30, "city": "NYC"}
print(person["name"])
person["email"] = "alice@example.com"
person["age"] = 31
print(person)
print(person.keys())
print(person.values())
print(person.items())
print("name" in person)
person.pop("city")
print(person.get("missing", "N/A"))
""",

    "Functions": """\
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

def add(a: int, b: int) -> int:
    return a + b

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(greet("Alice"))
print(greet("Bob", "Hi"))
print(add(3, 4))
print(factorial(5))
""",

    "List Comprehension": """\
squares = [x**2 for x in range(1, 11)]
print(squares)

evens = [x for x in range(20) if x % 2 == 0]
print(evens)

matrix = [[i * j for j in range(1, 4)] for i in range(1, 4)]
for row in matrix:
    print(row)
""",

    "Iterators": """\
nums = [1, 2, 3, 4, 5]
it = iter(nums)
print(next(it))
print(next(it))
print(next(it))

for i, val in enumerate(["a", "b", "c"], start=1):
    print(i, val)

pairs = list(zip([1,2,3], ["a","b","c"]))
print(pairs)
""",

    "Match / Case": """\
def http_status(code):
    match code:
        case 200:
            return "OK"
        case 404:
            return "Not Found"
        case 500:
            return "Server Error"
        case _:
            return "Unknown"

for c in [200, 404, 500, 418]:
    print(c, "->", http_status(c))
""",

    "Classes": """\
class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound

    def speak(self):
        return self.name + " says " + self.sound

class Dog(Animal):
    def __init__(self, name):
        self.name = name
        self.sound = "Woof"

    def fetch(self, item):
        return self.name + " fetches the " + item

dog = Dog("Rex")
print(dog.speak())
print(dog.fetch("ball"))
""",

    "Exception Handling": """\
def safe_divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError:
        return "Cannot divide by zero"
    except TypeError as e:
        return "Type error: " + str(e)
    else:
        return result
    finally:
        print("Division attempted")

print(safe_divide(10, 2))
print(safe_divide(10, 0))
""",

    "Lambda & Higher-Order": """\
double = lambda x: x * 2
square = lambda x: x ** 2

nums = [1, 2, 3, 4, 5]
print(list(map(double, nums)))
print(list(filter(lambda x: x % 2 == 0, nums)))
print(sorted(nums, key=lambda x: -x))

def apply(fn, val):
    return fn(val)

print(apply(square, 7))
""",

    "Arrays (via lists)": """\
import math

# Array operations
arr = [3, 1, 4, 1, 5, 9, 2, 6]
print("Original:", arr)
print("Sorted:", sorted(arr))
print("Max:", max(arr))
print("Min:", min(arr))
print("Sum:", sum(arr))
print("Length:", len(arr))

# 2D array
matrix = [[0] * 3 for _ in range(3)]
for i in range(3):
    for j in range(3):
        matrix[i][j] = i * 3 + j
for row in matrix:
    print(row)
""",
}

# ─── sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg", width=60)
    st.title("Mini Python Compiler")
    st.caption("Lexer → Parser → AST → Semantic → Interpreter")
    st.divider()
    st.subheader("📚 Examples")
    selected = st.selectbox("Load example:", list(EXAMPLES.keys()))
    load_btn = st.button("Load Example", use_container_width=True)
    st.divider()
    st.subheader("⚙️ Options")
    strict_mode = st.toggle("Strict semantic errors", value=False)
    show_tokens = st.toggle("Show token stream", value=False)
    st.divider()
    st.caption("Covers: Variables, Strings, Booleans, Operators, "
               "Lists, Tuples, Sets, Dicts, If/Else, Match, While, "
               "For, Functions, Range, Arrays, Iterators, Classes, "
               "Lambda, Comprehensions, Try/Except")

# ─── main area ────────────────────────────────────────────────────────────────

st.header("Mini Python Compiler — Interactive Demo")

# Initialize session state
if 'code' not in st.session_state:
    st.session_state.code = EXAMPLES["Hello World"]

if 'load_btn' not in st.session_state:
    st.session_state.load_btn = False

if st.button("Load Example", key="load_example"):
    st.session_state.load_btn = True
    st.session_state.code = EXAMPLES[selected]

# Reset after loading so it doesn't fire repeatedly
if st.session_state.load_btn:
    st.session_state.load_btn = False

# Code editor
code = st.text_area(
    "Enter your code here:",
    value=st.session_state.get("code", EXAMPLES["Hello World"]),
    height=280,
    key="editor"
    help="Write mini-Python code and click Run"
)
st.session_state.code = code

col_run, col_clear = st.columns([1, 5])
with col_run:
    run_btn = st.button(" Run", type="primary", use_container_width=True)
with col_clear:
    if st.button(" Clear"):
        st.session_state.code = ""
        st.rerun()

# ─── compilation & execution ─────────────────────────────────────────────────

if run_btn and code.strip():
    # Stage 1: Lex
    tokens = None
    ast = None
    sa = None
    output = ""
    exec_history = []
    sem_errors = []
    sem_warnings = []
    runtime_errors = []
    lex_error = None
    parse_error = None

    with st.spinner("Compiling..."):
        try:
            tokens = tokenize(code)
        except Exception as e:
            lex_error = str(e)

        if tokens and not lex_error:
            try:
                ast = Parser(tokens).parse()
            except Exception as e:
                parse_error = str(e)

        if ast and not parse_error:
            sa = SemanticAnalyzer()
            sem_errors = sa.analyze(ast)
            sem_warnings = sa.warnings

        if ast and (not sem_errors or not strict_mode):
            buf = io.StringIO()
            interp = Interpreter(stdout=buf)
            try:
                interp.execute(ast)
                output = buf.getvalue()
                exec_history = interp.execution_history
            except Exception as e:
                runtime_errors.append(str(e))
                output = buf.getvalue()
                exec_history = interp.execution_history

    # ── results tabs ──────────────────────────────────────────────────────────

    tab_out, tab_ast, tab_sym, tab_hist, tab_tok = st.tabs([
        "📤 Output", "🌳 AST", "📋 Symbol Table", "📜 History", "🔤 Tokens"
    ])

    # ── Output tab ────────────────────────────────────────────────────────────
    with tab_out:
        if lex_error:
            st.markdown(f'<div class="error-box">❌ Lexer Error:\n{lex_error}</div>',
                        unsafe_allow_html=True)
        elif parse_error:
            st.markdown(f'<div class="error-box">❌ Parse Error:\n{parse_error}</div>',
                        unsafe_allow_html=True)
        else:
            if sem_warnings:
                st.markdown(
                    '<div class="warn-box">⚠️ Warnings:\n' +
                    '\n'.join(sem_warnings) + '</div>',
                    unsafe_allow_html=True
                )
                st.write("")

            if sem_errors and strict_mode:
                st.markdown(
                    '<div class="error-box">❌ Semantic Errors:\n' +
                    '\n'.join(str(e) for e in sem_errors) + '</div>',
                    unsafe_allow_html=True
                )
            else:
                if sem_errors:
                    st.markdown(
                        '<div class="warn-box">⚠️ Semantic Warnings (running anyway):\n' +
                        '\n'.join(str(e) for e in sem_errors) + '</div>',
                        unsafe_allow_html=True
                    )
                    st.write("")

                if runtime_errors:
                    st.markdown(
                        f'<div class="error-box">❌ Runtime Error:\n{chr(10).join(runtime_errors)}</div>',
                        unsafe_allow_html=True
                    )
                    if output:
                        st.write("**Partial output:**")

                if output:
                    st.markdown(
                        f'<div class="output-box">{output}</div>',
                        unsafe_allow_html=True
                    )
                elif not runtime_errors:
                    st.markdown(
                        '<div class="output-box"><em style="color:#666">(no output)</em></div>',
                        unsafe_allow_html=True
                    )

    # ── AST tab ───────────────────────────────────────────────────────────────
    with tab_ast:
        if ast:
            def render_ast(node, depth=0) -> str:
                indent = "│  " * depth
                connector = "├─ " if depth > 0 else ""
                lines = [f"{indent}{connector}{repr(node)}"]
                child_attrs = ['statements', 'body', 'else_body', 'value',
                               'condition', 'left', 'right', 'args', 'elements',
                               'pairs', 'params']
                for attr in child_attrs:
                    val = getattr(node, attr, None)
                    if val is None:
                        continue
                    if isinstance(val, list):
                        for item in val:
                            if hasattr(item, '__class__') and hasattr(item, 'line'):
                                lines.append(render_ast(item, depth + 1))
                    elif hasattr(val, '__class__') and hasattr(val, 'line'):
                        lines.append(render_ast(val, depth + 1))
                return '\n'.join(lines)

            tree_str = render_ast(ast)
            st.markdown(f'<div class="ast-box">{tree_str}</div>', unsafe_allow_html=True)
        else:
            st.info("AST not available (compilation failed)")

    # ── Symbol Table tab ──────────────────────────────────────────────────────
    with tab_sym:
        if sa:
            snapshot = sa.snapshots[-1] if sa.snapshots else {}
            if snapshot:
                kind_badge = {
                    'variable': '<span class="badge badge-var">var</span>',
                    'function': '<span class="badge badge-fn">fn</span>',
                    'class':    '<span class="badge badge-cls">class</span>',
                    'module':   '<span class="badge badge-mod">mod</span>',
                    'parameter': '<span class="badge badge-var">param</span>',
                }
                rows = []
                for name, info in sorted(snapshot.items()):
                    badge = kind_badge.get(info['kind'], '')
                    type_str = info.get('type') or ''
                    line_str = str(info.get('line') or '')
                    rows.append({
                        'Name': name,
                        'Kind': info['kind'],
                        'Type Hint': type_str,
                        'Line': line_str,
                    })
                st.table(rows)
            else:
                st.info("No user-defined symbols found.")

    # ── History tab ───────────────────────────────────────────────────────────
    with tab_hist:
        if exec_history:
            st.write(f"**{len(exec_history)} execution steps**")
            max_steps = min(200, len(exec_history))
            min_steps = min(5, max_steps)
            default_steps = min(50, max_steps)
            if min_steps < max_steps:
                limit = st.slider("Show last N steps:", min_steps, max_steps, default_steps)
            else:
                limit = max_steps
                st.caption(f"Showing all {limit} step(s)")
            shown = exec_history[-limit:]
            for i, step in enumerate(shown):
                with st.expander(f"Step {len(exec_history)-limit+i+1}: {step['node']} "
                                 f"(line {step['line']})"):
                    scope = {k: repr(v)[:80] for k, v in step['scope'].items()
                             if not callable(v) and k not in ('print', 'len', 'range')}
                    if scope:
                        st.json(scope)
                    else:
                        st.caption("(empty scope)")
        else:
            st.info("No execution history available.")

    # ── Tokens tab ────────────────────────────────────────────────────────────
    with tab_tok:
        if show_tokens and tokens:
            display = [
                {'Type': t.type, 'Value': repr(t.value), 'Line': t.line, 'Col': t.col}
                for t in tokens if t.type not in ('NEWLINE', 'INDENT', 'DEDENT', 'EOF')
            ]
            st.write(f"**{len(display)} tokens**")
            st.dataframe(display, use_container_width=True, height=400)
        elif not show_tokens:
            st.info('Enable "Show token stream" in the sidebar to see tokens.')
        else:
            st.info("Token stream not available (lexer failed).")

elif run_btn:
    st.warning("Please enter some code first.")
