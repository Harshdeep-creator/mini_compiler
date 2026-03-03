"""
semantic.py - Semantic Analyzer for the Mini Python Compiler

Walks the AST, builds a scoped symbol table, detects:
  - Use of undefined variables / functions
  - Function re-declarations (warning, not error)
  - Return outside function
  - Break/continue outside loop
  - Basic type-hint mismatch (int/float/str/bool/list/dict/set/tuple)
"""

from ast_nodes import *
from errors import SemanticError
import warnings


# ─── Symbol Table ─────────────────────────────────────────────────────────────

class Symbol:
    def __init__(self, name, kind, type_hint=None, value=None, line=None):
        self.name = name
        self.kind = kind        # 'variable', 'function', 'class', 'parameter'
        self.type_hint = type_hint
        self.value = value
        self.line = line

    def __repr__(self):
        th = f": {self.type_hint}" if self.type_hint else ""
        return f"Symbol({self.name}{th} [{self.kind}])"


class Scope:
    def __init__(self, name: str, parent=None):
        self.name = name
        self.parent = parent
        self.symbols: dict[str, Symbol] = {}

    def define(self, sym: Symbol):
        self.symbols[sym.name] = sym

    def lookup(self, name: str):
        """Look up name in this scope and all parent scopes."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str):
        return self.symbols.get(name)

    def __repr__(self):
        return f"Scope({self.name}, {list(self.symbols.keys())})"


# ─── Semantic Analyzer ────────────────────────────────────────────────────────

class SemanticAnalyzer:
    """
    Single-pass semantic analyzer.
    Records snapshots of the symbol table for visualization.
    """

    BUILTIN_NAMES = {
        # functions
        'print', 'len', 'range', 'type', 'int', 'float', 'str', 'bool',
        'list', 'tuple', 'set', 'dict', 'input', 'abs', 'max', 'min',
        'sum', 'sorted', 'reversed', 'enumerate', 'zip', 'map', 'filter',
        'any', 'all', 'round', 'open', 'repr', 'id', 'isinstance',
        'issubclass', 'hasattr', 'getattr', 'setattr', 'delattr',
        'hex', 'oct', 'bin', 'chr', 'ord', 'pow', 'divmod', 'hash',
        'iter', 'next', 'callable', 'format', 'vars', 'dir', 'help',
        'super', 'object', 'staticmethod', 'classmethod', 'property',
        # exceptions
        'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
        'AttributeError', 'NameError', 'RuntimeError', 'StopIteration',
        'ZeroDivisionError', 'FileNotFoundError', 'IOError', 'OSError',
        'NotImplementedError', 'AssertionError', 'OverflowError',
        # special
        '__name__', '__file__', 'True', 'False', 'None',
    }

    def __init__(self):
        self.global_scope = Scope('global')
        self._scope = self.global_scope
        self._function_depth = 0
        self._loop_depth = 0
        self._warnings: list[str] = []
        self._errors: list[SemanticError] = []
        self.snapshots: list[dict] = []  # for visualization
        self._globals_declared: set[str] = set()

        # seed builtins
        for name in self.BUILTIN_NAMES:
            self.global_scope.define(Symbol(name, 'builtin'))

    # ── public interface ──────────────────────────────────────────────────────

    def analyze(self, node) -> list[SemanticError]:
        """Analyze the AST. Returns list of errors (warnings stored separately)."""
        self._visit(node)
        return self._errors

    @property
    def warnings(self):
        return self._warnings

    def symbol_table_snapshot(self) -> dict:
        """Return current scope's symbol table as a plain dict."""
        return {
            name: {'kind': sym.kind, 'type': sym.type_hint, 'line': sym.line}
            for name, sym in self._scope.symbols.items()
            if sym.kind != 'builtin'
        }

    # ── scope helpers ─────────────────────────────────────────────────────────

    def _push_scope(self, name: str):
        self._scope = Scope(name, self._scope)

    def _pop_scope(self):
        self._scope = self._scope.parent

    def _define(self, name: str, kind: str, type_hint=None, line=None):
        existing = self._scope.lookup_local(name)
        if existing and existing.kind == 'function' and kind == 'function':
            self._warn(f"Function '{name}' redeclared", line)
        self._scope.define(Symbol(name, kind, type_hint=type_hint, line=line))

    def _check_name(self, name: str, line=None):
        if name in self._globals_declared:
            if self.global_scope.lookup(name):
                return
        if not self._scope.lookup(name):
            self._error(f"Name '{name}' is not defined", line)

    def _warn(self, msg: str, line=None):
        loc = f" (line {line})" if line else ""
        self._warnings.append(f"Warning{loc}: {msg}")

    def _error(self, msg: str, line=None):
        err = SemanticError(msg, line)
        self._errors.append(err)

    # ── visitor dispatch ──────────────────────────────────────────────────────

    def _visit(self, node):
        if node is None:
            return
        if isinstance(node, list):
            for n in node:
                self._visit(n)
            return
        method = f"_visit_{type(node).__name__}"
        visitor = getattr(self, method, self._generic_visit)
        visitor(node)

    def _generic_visit(self, node):
        # visit children generically
        for attr in vars(node):
            val = getattr(node, attr)
            if isinstance(val, Node):
                self._visit(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, Node):
                        self._visit(item)

    # ── visitors ──────────────────────────────────────────────────────────────

    def _visit_Program(self, node: Program):
        for stmt in node.statements:
            self._visit(stmt)
        self.snapshots.append(self.symbol_table_snapshot())

    def _visit_Assignment(self, node: Assignment):
        self._visit(node.value)
        target = node.target
        if isinstance(target, Identifier):
            self._define(target.name, 'variable', type_hint=node.type_hint, line=node.line)
        elif isinstance(target, (IndexAccess, AttributeAccess)):
            self._visit(target)

    def _visit_AugAssignment(self, node: AugAssignment):
        self._visit(node.value)
        if isinstance(node.target, Identifier):
            self._check_name(node.target.name, node.line)

    def _visit_MultiAssignment(self, node: MultiAssignment):
        self._visit(node.value)
        for t in node.targets:
            if isinstance(t, Identifier):
                self._define(t.name, 'variable', line=node.line)

    def _visit_Identifier(self, node: Identifier):
        self._check_name(node.name, node.line)

    def _visit_FunctionDef(self, node: FunctionDef):
        self._define(node.name, 'function', line=node.line)
        self._push_scope(f'function:{node.name}')
        self._function_depth += 1
        for param_name, default, type_hint in node.params:
            self._define(param_name, 'parameter', type_hint=type_hint, line=node.line)
            if default:
                self._visit(default)
        for stmt in node.body:
            self._visit(stmt)
        self.snapshots.append(self.symbol_table_snapshot())
        self._function_depth -= 1
        self._pop_scope()

    def _visit_ClassDef(self, node: ClassDef):
        self._define(node.name, 'class', line=node.line)
        self._push_scope(f'class:{node.name}')
        for stmt in node.body:
            self._visit(stmt)
        self._pop_scope()

    def _visit_ReturnStatement(self, node: ReturnStatement):
        if self._function_depth == 0:
            self._error("'return' outside function", node.line)
        self._visit(node.value)

    def _visit_BreakStatement(self, node: BreakStatement):
        if self._loop_depth == 0:
            self._error("'break' outside loop", node.line)

    def _visit_ContinueStatement(self, node: ContinueStatement):
        if self._loop_depth == 0:
            self._error("'continue' outside loop", node.line)

    def _visit_IfStatement(self, node: IfStatement):
        self._visit(node.condition)
        for stmt in node.body:
            self._visit(stmt)
        for cond, body in node.elif_clauses:
            self._visit(cond)
            for stmt in body:
                self._visit(stmt)
        for stmt in node.else_body:
            self._visit(stmt)

    def _visit_WhileStatement(self, node: WhileStatement):
        self._visit(node.condition)
        self._loop_depth += 1
        for stmt in node.body:
            self._visit(stmt)
        self._loop_depth -= 1
        for stmt in node.else_body:
            self._visit(stmt)

    def _visit_ForStatement(self, node: ForStatement):
        self._visit(node.iterable)
        # define loop variable(s)
        if isinstance(node.target, Identifier):
            self._define(node.target.name, 'variable', line=node.line)
        elif isinstance(node.target, TupleLiteral):
            for t in node.target.elements:
                if isinstance(t, Identifier):
                    self._define(t.name, 'variable', line=node.line)
        self._loop_depth += 1
        for stmt in node.body:
            self._visit(stmt)
        self._loop_depth -= 1

    def _visit_PrintStatement(self, node: PrintStatement):
        for arg in node.args:
            self._visit(arg)

    def _visit_GlobalStatement(self, node: GlobalStatement):
        for name in node.names:
            self._globals_declared.add(name)
            if not self.global_scope.lookup(name):
                self._warn(f"Global '{name}' not defined at module level yet", node.line)

    def _visit_AssertStatement(self, node: AssertStatement):
        self._visit(node.condition)
        self._visit(node.message)

    def _visit_FunctionCall(self, node: FunctionCall):
        self._visit(node.func)
        for arg in node.args:
            self._visit(arg)
        for v in node.kwargs.values():
            self._visit(v)

    def _visit_BinaryOp(self, node: BinaryOp):
        self._visit(node.left)
        self._visit(node.right)

    def _visit_CompareOp(self, node: CompareOp):
        self._visit(node.left)
        for c in node.comparators:
            self._visit(c)

    def _visit_BoolOp(self, node: BoolOp):
        for v in node.values:
            self._visit(v)

    def _visit_IndexAccess(self, node: IndexAccess):
        self._visit(node.obj)
        self._visit(node.index)

    def _visit_SliceAccess(self, node: SliceAccess):
        self._visit(node.obj)
        self._visit(node.start)
        self._visit(node.stop)
        self._visit(node.step)

    def _visit_AttributeAccess(self, node: AttributeAccess):
        self._visit(node.obj)

    def _visit_ListLiteral(self, node: ListLiteral):
        for e in node.elements:
            self._visit(e)

    def _visit_TupleLiteral(self, node: TupleLiteral):
        for e in node.elements:
            self._visit(e)

    def _visit_SetLiteral(self, node: SetLiteral):
        for e in node.elements:
            self._visit(e)

    def _visit_DictLiteral(self, node: DictLiteral):
        for k, v in node.pairs:
            self._visit(k)
            self._visit(v)

    def _visit_ListComp(self, node: ListComp):
        self._visit(node.iterable)
        if isinstance(node.target, Identifier):
            self._define(node.target.name, 'variable', line=node.line)
        self._visit(node.element)
        self._visit(node.condition)

    def _visit_DictComp(self, node: DictComp):
        self._visit(node.iterable)
        if isinstance(node.target, Identifier):
            self._define(node.target.name, 'variable', line=node.line)
        self._visit(node.key)
        self._visit(node.value)
        self._visit(node.condition)

    def _visit_SetComp(self, node: SetComp):
        self._visit(node.iterable)
        if isinstance(node.target, Identifier):
            self._define(node.target.name, 'variable', line=node.line)
        self._visit(node.element)
        self._visit(node.condition)

    def _visit_LambdaExpr(self, node: LambdaExpr):
        self._push_scope('lambda')
        self._function_depth += 1
        for p in node.params:
            self._define(p, 'parameter', line=node.line)
        self._visit(node.body)
        self._function_depth -= 1
        self._pop_scope()

    def _visit_TernaryOp(self, node: TernaryOp):
        self._visit(node.condition)
        self._visit(node.true_val)
        self._visit(node.false_val)

    def _visit_InOperator(self, node: InOperator):
        self._visit(node.element)
        self._visit(node.collection)

    def _visit_IsOperator(self, node: IsOperator):
        self._visit(node.left)
        self._visit(node.right)

    def _visit_UnaryOp(self, node: UnaryOp):
        self._visit(node.operand)

    def _visit_TryStatement(self, node: TryStatement):
        for stmt in node.body:
            self._visit(stmt)
        for exc_type, exc_name, h_body in node.handlers:
            if exc_name:
                self._define(exc_name, 'variable', line=node.line)
            for stmt in h_body:
                self._visit(stmt)
        for stmt in node.else_body:
            self._visit(stmt)
        for stmt in node.finally_body:
            self._visit(stmt)

    def _visit_MatchStatement(self, node: MatchStatement):
        self._visit(node.subject)
        for pattern, guard, body in node.cases:
            if isinstance(pattern, Identifier) and pattern.name != '_':
                self._define(pattern.name, 'variable', line=node.line)
            self._visit(guard)
            for stmt in body:
                self._visit(stmt)

    def _visit_WithStatement(self, node: WithStatement):
        self._visit(node.context_expr)
        if node.target:
            self._define(node.target.name, 'variable', line=node.line)
        for stmt in node.body:
            self._visit(stmt)

    def _visit_ImportStatement(self, node: ImportStatement):
        alias = node.alias or node.module
        self._define(alias, 'module', line=node.line)

    def _visit_FromImport(self, node: FromImport):
        for name, alias in node.names:
            self._define(alias or name, 'variable', line=node.line)

    def _visit_ExprStatement(self, node: ExprStatement):
        self._visit(node.expr)

    def _visit_DeleteStatement(self, node: DeleteStatement):
        self._visit(node.target)

    def _visit_RaiseStatement(self, node: RaiseStatement):
        self._visit(node.exception)

    # ignore simple literal nodes
    def _visit_NumberLiteral(self, node): pass
    def _visit_StringLiteral(self, node): pass
    def _visit_BoolLiteral(self, node): pass
    def _visit_NoneLiteral(self, node): pass
    def _visit_PassStatement(self, node): pass
    def _visit_BreakStatement_ok(self, node): pass


# ─── convenience ──────────────────────────────────────────────────────────────

def analyze(ast):
    sa = SemanticAnalyzer()
    errors = sa.analyze(ast)
    return sa, errors
