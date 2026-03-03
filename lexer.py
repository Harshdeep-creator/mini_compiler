"""
lexer.py - Lexer / Tokenizer for the Mini Python Compiler

Produces a stream of (type, value, line, col) Token objects.
Handles: keywords, identifiers, numbers (int/float), strings (single/double/triple),
         operators, delimiters, indentation (INDENT/DEDENT/NEWLINE), comments.
"""

import re
from errors import LexerError

# ─── Token ───────────────────────────────────────────────────────────────────

class Token:
    __slots__ = ('type', 'value', 'line', 'col')

    def __init__(self, type_, value, line=0, col=0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, L{self.line}:C{self.col})"


# ─── Keywords ────────────────────────────────────────────────────────────────

KEYWORDS = {
    'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
    'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global',
    'if', 'import', 'in', 'is', 'lambda', 'match', 'case', 'None', 'not',
    'or', 'pass', 'print', 'raise', 'return', 'True', 'try', 'while',
    'with', 'yield',
}

# ─── Lexer ────────────────────────────────────────────────────────────────────

class Lexer:
    """
    Tokenizes source code into a flat list of Token objects.
    Generates NEWLINE, INDENT, DEDENT tokens for block structure.
    """

    # Master regex – order matters: longer patterns first
    TOKEN_SPEC = [
        ('TRIPLE_DSTRING', r'"""(?:[^"\\]|\\.|"{1,2}(?!"))*"""'),
        ('TRIPLE_SSTRING', r"'''(?:[^'\\]|\\.|'{1,2}(?!'))*'''"),
        ('DSTRING',        r'"(?:[^"\\\n]|\\.)*"'),
        ('SSTRING',        r"'(?:[^'\\\n]|\\.)*'"),
        ('FLOAT',          r'\d+\.\d*|\.\d+'),
        ('INT',            r'0[xX][0-9a-fA-F]+|0[oO][0-7]+|0[bB][01]+|\d+'),
        ('AUG_ASSIGN',     r'\*\*=|//=|<<=|>>=|[+\-*/%&|^]='),
        ('POWER',          r'\*\*'),
        ('FLOOR_DIV',      r'//'),
        ('LSHIFT',         r'<<'),
        ('RSHIFT',         r'>>'),
        ('ARROW',          r'->'),
        ('WALRUS',         r':='),
        ('LE',             r'<='),
        ('GE',             r'>='),
        ('EQ',             r'=='),
        ('NE',             r'!='),
        ('LT',             r'<'),
        ('GT',             r'>'),
        ('ASSIGN',         r'='),
        ('PLUS',           r'\+'),
        ('MINUS',          r'-'),
        ('STAR',           r'\*'),
        ('SLASH',          r'/'),
        ('PERCENT',        r'%'),
        ('AMPERSAND',      r'&'),
        ('PIPE',           r'\|'),
        ('CARET',          r'\^'),
        ('TILDE',          r'~'),
        ('DOT',            r'\.'),
        ('COMMA',          r','),
        ('SEMICOLON',      r';'),
        ('COLON',          r':'),
        ('AT',             r'@'),
        ('LPAREN',         r'\('),
        ('RPAREN',         r'\)'),
        ('LBRACKET',       r'\['),
        ('RBRACKET',       r'\]'),
        ('LBRACE',         r'\{'),
        ('RBRACE',         r'\}'),
        ('NAME',           r'[A-Za-z_][A-Za-z0-9_]*'),
        ('COMMENT',        r'#[^\n]*'),
        ('NEWLINE',        r'\n'),
        ('WS',             r'[ \t]+'),
        ('BACKSLASH',      r'\\[ \t]*\n'),   # line continuation
        ('MISMATCH',       r'.'),
    ]

    MASTER_RE = re.compile(
        '|'.join(f'(?P<{name}>{pat})' for name, pat in TOKEN_SPEC),
        re.DOTALL
    )

    def __init__(self, source: str):
        self.source = source
        self.tokens: list[Token] = []
        self._indent_stack = [0]
        self._paren_depth = 0   # inside () [] {} → ignore newlines

    # ── public entry point ────────────────────────────────────────────────────

    def tokenize(self) -> list[Token]:
        lines = self.source.split('\n')
        self._tokenize_lines(lines)
        # flush remaining dedents
        while len(self._indent_stack) > 1:
            self._indent_stack.pop()
            self.tokens.append(Token('DEDENT', '', len(lines), 0))
        self.tokens.append(Token('EOF', '', len(lines), 0))
        return self.tokens

    # ── internal helpers ──────────────────────────────────────────────────────

    def _tokenize_lines(self, lines):
        """Process source line by line to handle indentation correctly."""
        # Rejoin for the master regex – we track position manually
        source = self.source
        line_num = 1
        line_start = 0
        pending_newline = False  # emit NEWLINE before next real token

        # We process with the master regex over the full source
        for m in self.MASTER_RE.finditer(source):
            kind = m.lastgroup
            value = m.group()
            col = m.start() - line_start + 1

            if kind == 'NEWLINE':
                line_num += 1
                line_start = m.end()
                if self._paren_depth == 0:
                    pending_newline = True
                continue

            if kind == 'BACKSLASH':
                # line continuation – skip
                line_num += 1
                line_start = m.end()
                continue

            if kind == 'WS':
                # only relevant at start of line for indentation
                continue

            if kind == 'COMMENT':
                continue

            if kind == 'MISMATCH':
                raise LexerError(f"Unexpected character: {repr(value)}", line_num, col)

            # ── handle indentation via pending_newline ──
            if pending_newline and self._paren_depth == 0:
                pending_newline = False
                # figure out indent of current token
                tok_start = m.start()
                # find start of this line
                line_begin = source.rfind('\n', 0, tok_start) + 1
                indent = tok_start - line_begin
                self._handle_indent(indent, line_num, col)
                self.tokens.append(Token('NEWLINE', '\n', line_num - 1, 0))

            # ── process token ──
            if kind == 'LPAREN' or kind == 'LBRACKET' or kind == 'LBRACE':
                self._paren_depth += 1
            elif kind == 'RPAREN' or kind == 'RBRACKET' or kind == 'RBRACE':
                self._paren_depth -= 1

            if kind in ('TRIPLE_DSTRING', 'TRIPLE_SSTRING', 'DSTRING', 'SSTRING'):
                # count embedded newlines
                newlines_in_str = value.count('\n')
                line_num += newlines_in_str
                if newlines_in_str:
                    line_start = m.end() - (len(value) - value.rfind('\n') - 1)
                tok = Token('STRING', self._unescape(value), line_num, col)
                self.tokens.append(tok)

            elif kind == 'FLOAT':
                self.tokens.append(Token('FLOAT', float(value), line_num, col))

            elif kind == 'INT':
                self.tokens.append(Token('INT', int(value, 0), line_num, col))

            elif kind == 'NAME':
                if value in KEYWORDS:
                    tok_type = value.upper() if value not in ('match', 'case') else value.upper()
                    # Special: True/False/None keep their Python values
                    if value == 'True':
                        self.tokens.append(Token('TRUE', True, line_num, col))
                    elif value == 'False':
                        self.tokens.append(Token('FALSE', False, line_num, col))
                    elif value == 'None':
                        self.tokens.append(Token('NONE', None, line_num, col))
                    else:
                        self.tokens.append(Token(value.upper(), value, line_num, col))
                else:
                    self.tokens.append(Token('NAME', value, line_num, col))

            elif kind == 'AUG_ASSIGN':
                self.tokens.append(Token('AUG_ASSIGN', value, line_num, col))

            else:
                self.tokens.append(Token(kind, value, line_num, col))

        # end-of-file: emit NEWLINE + DEDENTs
        if self._paren_depth == 0:
            self.tokens.append(Token('NEWLINE', '\n', line_num, 0))

    def _handle_indent(self, indent: int, line: int, col: int):
        current = self._indent_stack[-1]
        if indent > current:
            self._indent_stack.append(indent)
            self.tokens.append(Token('INDENT', indent, line, 1))
        elif indent < current:
            while self._indent_stack[-1] > indent:
                self._indent_stack.pop()
                self.tokens.append(Token('DEDENT', indent, line, 1))
            if self._indent_stack[-1] != indent:
                raise LexerError(f"Inconsistent indentation", line, col)

    @staticmethod
    def _unescape(s: str) -> str:
        """Strip quotes and process escape sequences."""
        if s.startswith('"""') or s.startswith("'''"):
            s = s[3:-3]
        elif s.startswith('"') or s.startswith("'"):
            s = s[1:-1]
        return s.encode('raw_unicode_escape').decode('unicode_escape', errors='replace')


# ─── Convenience ─────────────────────────────────────────────────────────────

def tokenize(source: str) -> list[Token]:
    return Lexer(source).tokenize()


if __name__ == '__main__':
    import sys
    src = sys.stdin.read() if len(sys.argv) < 2 else open(sys.argv[1]).read()
    for tok in tokenize(src):
        if tok.type not in ('NEWLINE', 'INDENT', 'DEDENT', 'EOF'):
            print(tok)
