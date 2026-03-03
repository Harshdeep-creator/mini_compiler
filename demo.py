import sys
import os
import io

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

# ─── example programs ─────────────────────────────────────────────────────────
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
print(a // b)   # 3
print(a % b)   # 1
print(a ** b)   # 1000
""",
    # ... include other examples as in your original code ...
}

# ─── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg", width=60)
    st.title("Mini Python Compiler")
    st.caption("Lexer → Parser → AST → Semantic → Interpreter")
    st.divider()
    
    st.subheader("📚 Examples")
    # unique key to avoid duplicate ID error
    selected = st.selectbox("Load example:", list(EXAMPLES.keys()), key="example_select")
    if st.button("Load Example", key="load_example"):
        st.session_state.code = EXAMPLES[selected]

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
st.header("🐍 Mini Python Compiler — Interactive Demo")

# Initialize session state
if 'code' not in st.session_state:
    st.session_state.code = EXAMPLES["Hello World"]

# Code editor
code = st.text_area(
    "Enter your code here:",
    value=st.session_state.code,
    height=280,
    key="editor",
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
    tokens = ast = sa = None
    output = ""
    exec_history = []
    sem_errors = []
    sem_warnings = []
    runtime_errors = []
    lex_error = parse_error = None

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
                if runtime_errors:
                    st.markdown(
                        f'<div class="error-box">❌ Runtime Error:\n{chr(10).join(runtime_errors)}</div>',
                        unsafe_allow_html=True
                    )
                if output:
                    st.markdown(f'<div class="output-box">{output}</div>', unsafe_allow_html=True)
                elif not runtime_errors:
                    st.markdown('<div class="output-box"><em style="color:#666">(no output)</em></div>', unsafe_allow_html=True)

# Optionally, you can keep the rest of AST / Symbol Table / History / Tokens tabs as in your original code
