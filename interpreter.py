"""
interpreter.py - Tree-walking interpreter for the Mini Python Compiler

Executes the AST produced by parser.py.
Supports: variables, arithmetic, strings, booleans, None, lists, tuples,
          sets, dicts, if/elif/else, while, for, functions, classes,
          match/case, try/except/finally, with, comprehensions, lambdas,
          range, iterators, slices, augmented assignment, tuple unpacking,
          built-in functions (print, len, range, type, int, float, str,
          bool, list, tuple, set, dict, sorted, reversed, enumerate, zip,
          map, filter, sum, min, max, abs, round, input, chr, ord, hex,
          oct, bin, pow, divmod, any, all, repr, id, format, iter, next,
          isinstance, hasattr, getattr, setattr, open ...).
"""

import sys
import io
import math
from ast_nodes import *
from errors import RuntimeError_, BreakSignal, ContinueSignal, ReturnSignal


# ─── Environment (scope) ──────────────────────────────────────────────────────

class Environment:
    def __init__(self, parent=None, name='global'):
        self.parent = parent
        self.name = name
        self.vars: dict = {}
        self.globals_declared: set = set()

    def get(self, name: str, line=None):
        if name in self.globals_declared and self.parent:
            return self._get_global(name, line)
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get(name, line)
        raise RuntimeError_(f"Name '{name}' is not defined", line)

    def _get_global(self, name, line):
        env = self
        while env.parent:
            env = env.parent
        if name in env.vars:
            return env.vars[name]
        raise RuntimeError_(f"Global name '{name}' is not defined", line)

    def set(self, name: str, value, line=None):
        if name in self.globals_declared and self.parent:
            env = self
            while env.parent:
                env = env.parent
            env.vars[name] = value
            return
        self.vars[name] = value

    def delete(self, name: str, line=None):
        if name in self.vars:
            del self.vars[name]
        elif self.parent:
            self.parent.delete(name, line)
        else:
            raise RuntimeError_(f"Name '{name}' is not defined", line)

    def snapshot(self) -> dict:
        snap = {}
        if self.parent:
            snap.update(self.parent.snapshot())
        snap.update(self.vars)
        return snap


# ─── User-defined function & class ───────────────────────────────────────────

class UserFunction:
    def __init__(self, name, params, body, closure: Environment):
        self.name = name
        self.params = params    # list of (name, default, type_hint)
        self.body = body
        self.closure = closure

    def __repr__(self):
        return f"<function {self.name}>"

    def __call__(self, *args, **kwargs):
        # Called by the interpreter's _call helper
        raise NotImplementedError("Use interpreter._call_user_function")


class _BoundMethod:
    """Wraps a UserFunction with its bound instance for method calls."""
    def __init__(self, instance, fn):
        self.instance = instance
        self.fn = fn

    def __repr__(self):
        return f"<bound method {self.fn.name}>"


class UserClass:
    def __init__(self, name, bases, body, closure):
        self.name = name
        self.bases = bases
        self.body = body
        self.closure = closure

    def __repr__(self):
        return f"<class '{self.name}'>"


class UserInstance:
    def __init__(self, cls):
        self.cls = cls
        self.attrs = {}

    def __repr__(self):
        return f"<{self.cls.name} object>"

    def get_attr(self, name, line=None):
        if name in self.attrs:
            return self.attrs[name]
        # look in class body env
        if name in self.cls.__dict__.get('_env', {}):
            return self.cls._env[name]
        raise RuntimeError_(f"'{self.cls.name}' object has no attribute '{name}'", line)

    def set_attr(self, name, value):
        self.attrs[name] = value


# ─── Interpreter ─────────────────────────────────────────────────────────────

class Interpreter:
    def __init__(self, stdout=None):
        self.env = Environment(name='global')
        self.output_buffer = stdout or io.StringIO()
        self._execution_history: list[dict] = []
        self._setup_builtins()

    def _out(self, *args, sep=' ', end='\n'):
        text = sep.join(str(a) for a in args) + end
        self.output_buffer.write(text)

    def get_output(self) -> str:
        return self.output_buffer.getvalue()

    # ── built-ins ─────────────────────────────────────────────────────────────

    def _setup_builtins(self):
        interp = self
        env = self.env

        env.set('print',     lambda *a, **kw: interp._out(*a, **kw))
        env.set('len',       len)
        env.set('range',     range)
        env.set('type',      lambda x: type(x).__name__)
        env.set('int',       int)
        env.set('float',     float)
        env.set('str',       str)
        env.set('bool',      bool)
        env.set('list',      list)
        env.set('tuple',     tuple)
        env.set('set',       set)
        env.set('dict',      dict)
        env.set('abs',       abs)
        env.set('max',       max)
        env.set('min',       min)
        env.set('sum',       sum)
        env.set('round',     round)
        env.set('sorted',    sorted)
        env.set('reversed',  lambda x: list(reversed(x)))
        env.set('enumerate', enumerate)
        env.set('zip',       zip)
        env.set('map',       lambda f, *iters: list(map(f, *iters)))
        env.set('filter',    lambda f, it: list(filter(f, it)))
        env.set('any',       any)
        env.set('all',       all)
        env.set('repr',      repr)
        env.set('id',        id)
        env.set('chr',       chr)
        env.set('ord',       ord)
        env.set('hex',       hex)
        env.set('oct',       oct)
        env.set('bin',       bin)
        env.set('pow',       pow)
        env.set('divmod',    divmod)
        env.set('hash',      hash)
        env.set('format',    format)
        env.set('iter',      iter)
        env.set('next',      lambda it, *d: next(it, *d))
        env.set('callable',  callable)
        env.set('isinstance', isinstance)
        env.set('issubclass', issubclass)
        env.set('hasattr',   hasattr)
        env.set('getattr',   getattr)
        env.set('setattr',   setattr)
        env.set('input',     lambda prompt='': interp._builtin_input(prompt))
        env.set('open',      open)
        env.set('vars',      lambda o=None: vars(o) if o else {})
        env.set('dir',       dir)
        env.set('super',     super)
        env.set('object',    object)
        env.set('staticmethod', staticmethod)
        env.set('classmethod',  classmethod)
        env.set('property',     property)
        env.set('True',      True)
        env.set('False',     False)
        env.set('None',      None)
        # math
        env.set('math', math)
        # exceptions
        for exc in (Exception, ValueError, TypeError, KeyError, IndexError,
                    AttributeError, NameError, RuntimeError, StopIteration,
                    ZeroDivisionError, FileNotFoundError, AssertionError,
                    OverflowError, NotImplementedError, IOError, OSError):
            env.set(exc.__name__, exc)

    def _builtin_input(self, prompt=''):
        self._out(prompt, end='')
        return input()  # delegate to real stdin

    # ── public entry point ────────────────────────────────────────────────────

    def execute(self, program: Program):
        try:
            self._exec_stmts(program.statements, self.env)
        except ReturnSignal:
            pass  # top-level return
        except BreakSignal:
            raise RuntimeError_("'break' outside loop")
        except ContinueSignal:
            raise RuntimeError_("'continue' outside loop")

    # ── statement execution ───────────────────────────────────────────────────

    def _exec_stmts(self, stmts, env):
        for stmt in stmts:
            self._exec(stmt, env)

    def _exec(self, node, env):
        self._record(node, env)
        method = f"_exec_{type(node).__name__}"
        handler = getattr(self, method, self._exec_expr_fallback)
        return handler(node, env)

    def _exec_expr_fallback(self, node, env):
        # evaluate expression (e.g., function call as statement)
        return self._eval(node, env)

    def _record(self, node, env):
        self._execution_history.append({
            'node': repr(node),
            'line': getattr(node, 'line', None),
            'scope': env.snapshot()
        })

    # ── statement handlers ────────────────────────────────────────────────────

    def _exec_Program(self, node: Program, env):
        self._exec_stmts(node.statements, env)

    def _exec_Assignment(self, node: Assignment, env):
        value = self._eval(node.value, env)
        self._assign_target(node.target, value, env, node.line)

    def _exec_AugAssignment(self, node: AugAssignment, env):
        current = self._eval(node.target, env)
        operand = self._eval(node.value, env)
        ops = {'+': lambda a,b: a+b, '-': lambda a,b: a-b, '*': lambda a,b: a*b,
               '/': lambda a,b: a/b, '//': lambda a,b: a//b, '%': lambda a,b: a%b,
               '**': lambda a,b: a**b, '&': lambda a,b: a&b, '|': lambda a,b: a|b,
               '^': lambda a,b: a^b, '<<': lambda a,b: a<<b, '>>': lambda a,b: a>>b}
        result = ops[node.op](current, operand)
        self._assign_target(node.target, result, env, node.line)

    def _exec_MultiAssignment(self, node: MultiAssignment, env):
        value = self._eval(node.value, env)
        try:
            values = list(value)
        except TypeError:
            raise RuntimeError_(f"Cannot unpack non-iterable", node.line)
        if len(values) != len(node.targets):
            raise RuntimeError_(
                f"Not enough values to unpack (expected {len(node.targets)}, got {len(values)})",
                node.line
            )
        for target, val in zip(node.targets, values):
            self._assign_target(target, val, env, node.line)

    def _assign_target(self, target, value, env, line=None):
        if isinstance(target, Identifier):
            env.set(target.name, value, line)
        elif isinstance(target, IndexAccess):
            obj = self._eval(target.obj, env)
            idx = self._eval(target.index, env)
            obj[idx] = value
        elif isinstance(target, AttributeAccess):
            obj = self._eval(target.obj, env)
            if isinstance(obj, UserInstance):
                obj.attrs[target.attr] = value
            else:
                setattr(obj, target.attr, value)
        elif isinstance(target, TupleLiteral):
            # tuple unpacking
            try:
                vals = list(value)
            except TypeError:
                raise RuntimeError_(f"Cannot unpack non-iterable", line)
            if len(vals) != len(target.elements):
                raise RuntimeError_(
                    f"Not enough values to unpack (expected {len(target.elements)}, got {len(vals)})",
                    line
                )
            for t, v in zip(target.elements, vals):
                self._assign_target(t, v, env, line)
        else:
            raise RuntimeError_(f"Invalid assignment target: {repr(target)}", line)

    def _exec_ExprStatement(self, node: ExprStatement, env):
        self._eval(node.expr, env)

    def _exec_PrintStatement(self, node: PrintStatement, env):
        values = [self._eval(arg, env) for arg in node.args]
        self._out(*values, sep=node.sep, end=node.end)

    def _exec_IfStatement(self, node: IfStatement, env):
        if self._eval(node.condition, env):
            self._exec_stmts(node.body, env)
        else:
            for cond, body in node.elif_clauses:
                if self._eval(cond, env):
                    self._exec_stmts(body, env)
                    return
            self._exec_stmts(node.else_body, env)

    def _exec_WhileStatement(self, node: WhileStatement, env):
        ran = False
        while self._eval(node.condition, env):
            ran = True
            try:
                self._exec_stmts(node.body, env)
            except BreakSignal:
                return
            except ContinueSignal:
                continue
        if not ran or node.else_body:
            self._exec_stmts(node.else_body, env)

    def _exec_ForStatement(self, node: ForStatement, env):
        iterable = self._eval(node.iterable, env)
        broke = False
        for item in iterable:
            # assign loop target
            if isinstance(node.target, Identifier):
                env.set(node.target.name, item)
            elif isinstance(node.target, TupleLiteral):
                items = list(item)
                for t, v in zip(node.target.elements, items):
                    if isinstance(t, Identifier):
                        env.set(t.name, v)
            try:
                self._exec_stmts(node.body, env)
            except BreakSignal:
                broke = True
                break
            except ContinueSignal:
                continue
        if not broke:
            self._exec_stmts(node.else_body, env)

    def _exec_FunctionDef(self, node: FunctionDef, env):
        func = UserFunction(node.name, node.params, node.body, env)
        env.set(node.name, func)

    def _exec_ClassDef(self, node: ClassDef, env):
        class_env = Environment(parent=env, name=f'class:{node.name}')
        # resolve base classes
        base_classes = []
        for b in node.bases:
            try:
                base_classes.append(env.get(b))
            except Exception:
                pass
        cls = UserClass(node.name, base_classes, node.body, class_env)
        cls._env = class_env.vars
        # execute body in class env to collect methods/attrs
        self._exec_stmts(node.body, class_env)
        env.set(node.name, cls)

    def _exec_ReturnStatement(self, node: ReturnStatement, env):
        value = self._eval(node.value, env) if node.value is not None else None
        raise ReturnSignal(value)

    def _exec_BreakStatement(self, node: BreakStatement, env):
        raise BreakSignal()

    def _exec_ContinueStatement(self, node: ContinueStatement, env):
        raise ContinueSignal()

    def _exec_PassStatement(self, node: PassStatement, env):
        pass

    def _exec_GlobalStatement(self, node: GlobalStatement, env):
        for name in node.names:
            env.globals_declared.add(name)

    def _exec_DeleteStatement(self, node: DeleteStatement, env):
        target = node.target
        if isinstance(target, Identifier):
            env.delete(target.name, node.line)
        elif isinstance(target, IndexAccess):
            obj = self._eval(target.obj, env)
            idx = self._eval(target.index, env)
            del obj[idx]

    def _exec_AssertStatement(self, node: AssertStatement, env):
        val = self._eval(node.condition, env)
        if not val:
            msg = self._eval(node.message, env) if node.message else "Assertion failed"
            raise AssertionError(str(msg))

    def _exec_RaiseStatement(self, node: RaiseStatement, env):
        if node.exception:
            exc = self._eval(node.exception, env)
            raise exc if isinstance(exc, BaseException) else RuntimeError(str(exc))
        raise RuntimeError("raise")

    def _exec_TryStatement(self, node: TryStatement, env):
        try:
            self._exec_stmts(node.body, env)
        except (BreakSignal, ContinueSignal, ReturnSignal):
            raise
        except Exception as e:
            handled = False
            for exc_type, exc_name, h_body in node.handlers:
                if exc_type is None:
                    matched = True
                else:
                    try:
                        exc_cls = env.get(exc_type)
                        matched = isinstance(e, exc_cls)
                    except Exception:
                        matched = True
                if matched:
                    if exc_name:
                        env.set(exc_name, e)
                    self._exec_stmts(h_body, env)
                    handled = True
                    break
            if not handled:
                raise
        else:
            self._exec_stmts(node.else_body, env)
        finally:
            self._exec_stmts(node.finally_body, env)

    def _exec_WithStatement(self, node: WithStatement, env):
        ctx = self._eval(node.context_expr, env)
        with ctx as val:
            if node.target:
                env.set(node.target.name, val)
            self._exec_stmts(node.body, env)

    def _exec_MatchStatement(self, node: MatchStatement, env):
        subject = self._eval(node.subject, env)
        for pattern, guard, body in node.cases:
            if self._match_pattern(subject, pattern, env):
                if guard is None or self._eval(guard, env):
                    self._exec_stmts(body, env)
                    return

    def _match_pattern(self, value, pattern, env):
        """Simple pattern matching: wildcard, literal, or capture."""
        if isinstance(pattern, Identifier):
            if pattern.name == '_':
                return True  # wildcard
            env.set(pattern.name, value)
            return True
        if isinstance(pattern, (NumberLiteral, StringLiteral, BoolLiteral, NoneLiteral)):
            pat_val = self._eval(pattern, env)
            return value == pat_val
        return False

    def _exec_ImportStatement(self, node: ImportStatement, env):
        try:
            import importlib
            module = importlib.import_module(node.module)
            alias = node.alias or node.module
            env.set(alias, module)
        except ImportError as e:
            raise RuntimeError_(f"Cannot import '{node.module}': {e}", node.line)

    def _exec_FromImport(self, node: FromImport, env):
        try:
            import importlib
            module = importlib.import_module(node.module)
            for name, alias in node.names:
                val = getattr(module, name, None)
                env.set(alias or name, val)
        except ImportError as e:
            raise RuntimeError_(f"Cannot import from '{node.module}': {e}", node.line)

    # ── expression evaluation ─────────────────────────────────────────────────

    def _eval(self, node, env):
        if node is None:
            return None
        method = f"_eval_{type(node).__name__}"
        handler = getattr(self, method, None)
        if handler is None:
            raise RuntimeError_(f"Cannot evaluate node: {type(node).__name__}")
        return handler(node, env)

    def _eval_NumberLiteral(self, node: NumberLiteral, env):
        return node.value

    def _eval_StringLiteral(self, node: StringLiteral, env):
        return node.value

    def _eval_BoolLiteral(self, node: BoolLiteral, env):
        return node.value

    def _eval_NoneLiteral(self, node: NoneLiteral, env):
        return None

    def _eval_Identifier(self, node: Identifier, env):
        return env.get(node.name, node.line)

    def _eval_ListLiteral(self, node: ListLiteral, env):
        return [self._eval(e, env) for e in node.elements]

    def _eval_TupleLiteral(self, node: TupleLiteral, env):
        return tuple(self._eval(e, env) for e in node.elements)

    def _eval_SetLiteral(self, node: SetLiteral, env):
        return {self._eval(e, env) for e in node.elements}

    def _eval_DictLiteral(self, node: DictLiteral, env):
        return {self._eval(k, env): self._eval(v, env) for k, v in node.pairs}

    def _eval_BinaryOp(self, node: BinaryOp, env):
        l = self._eval(node.left, env)
        r = self._eval(node.right, env)
        ops = {
            '+': lambda a,b: a+b, '-': lambda a,b: a-b,
            '*': lambda a,b: a*b, '/': lambda a,b: a/b,
            '//': lambda a,b: a//b, '%': lambda a,b: a%b,
            '**': lambda a,b: a**b, '&': lambda a,b: a&b,
            '|': lambda a,b: a|b, '^': lambda a,b: a^b,
            '<<': lambda a,b: a<<b, '>>': lambda a,b: a>>b,
        }
        try:
            return ops[node.op](l, r)
        except ZeroDivisionError:
            raise ZeroDivisionError("division by zero")
        except TypeError as e:
            raise TypeError(str(e))
        except Exception as e:
            raise RuntimeError_(str(e), node.line)

    def _eval_UnaryOp(self, node: UnaryOp, env):
        val = self._eval(node.operand, env)
        if node.op == '-':  return -val
        if node.op == '+':  return +val
        if node.op == '~':  return ~val
        if node.op == 'not': return not val
        raise RuntimeError_(f"Unknown unary op: {node.op}", node.line)

    def _eval_CompareOp(self, node: CompareOp, env):
        left = self._eval(node.left, env)
        for op, comp_node in zip(node.ops, node.comparators):
            right = self._eval(comp_node, env)
            result = self._compare(left, op, right, node.line)
            if not result:
                return False
            left = right
        return True

    def _compare(self, left, op, right, line=None):
        try:
            if op == '<':       return left < right
            if op == '>':       return left > right
            if op == '<=':      return left <= right
            if op == '>=':      return left >= right
            if op == '==':      return left == right
            if op == '!=':      return left != right
            if op == 'in':      return left in right
            if op == 'not in':  return left not in right
            if op == 'is':      return left is right
            if op == 'is not':  return left is not right
        except TypeError as e:
            raise RuntimeError_(str(e), line)

    def _eval_BoolOp(self, node: BoolOp, env):
        if node.op == 'and':
            result = True
            for v in node.values:
                result = self._eval(v, env)
                if not result:
                    return result
            return result
        else:  # or
            result = False
            for v in node.values:
                result = self._eval(v, env)
                if result:
                    return result
            return result

    def _eval_InOperator(self, node: InOperator, env):
        elem = self._eval(node.element, env)
        coll = self._eval(node.collection, env)
        result = elem in coll
        return not result if node.negated else result

    def _eval_IsOperator(self, node: IsOperator, env):
        l = self._eval(node.left, env)
        r = self._eval(node.right, env)
        result = l is r
        return not result if node.negated else result

    def _eval_TernaryOp(self, node: TernaryOp, env):
        if self._eval(node.condition, env):
            return self._eval(node.true_val, env)
        return self._eval(node.false_val, env)

    def _eval_IndexAccess(self, node: IndexAccess, env):
        obj = self._eval(node.obj, env)
        idx = self._eval(node.index, env)
        try:
            return obj[idx]
        except (IndexError, KeyError) as e:
            raise RuntimeError_(str(e), node.line)

    def _eval_SliceAccess(self, node: SliceAccess, env):
        obj = self._eval(node.obj, env)
        start = self._eval(node.start, env) if node.start else None
        stop  = self._eval(node.stop, env)  if node.stop  else None
        step  = self._eval(node.step, env)  if node.step  else None
        return obj[start:stop:step]

    def _eval_AttributeAccess(self, node: AttributeAccess, env):
        obj = self._eval(node.obj, env)
        if isinstance(obj, UserInstance):
            # check instance attrs first
            if node.attr in obj.attrs:
                val = obj.attrs[node.attr]
                if isinstance(val, UserFunction):
                    return _BoundMethod(obj, val)
                return val
            # check class env
            cls_env = obj.cls._env
            if node.attr in cls_env:
                val = cls_env[node.attr]
                if isinstance(val, UserFunction):
                    return _BoundMethod(obj, val)
                return val
            raise RuntimeError_(f"'{obj.cls.name}' object has no attribute '{node.attr}'", node.line)
        try:
            return getattr(obj, node.attr)
        except AttributeError:
            raise RuntimeError_(f"'{type(obj).__name__}' has no attribute '{node.attr}'", node.line)

    def _eval_FunctionCall(self, node: FunctionCall, env):
        func = self._eval(node.func, env)
        args = [self._eval(a, env) for a in node.args]
        kwargs = {k: self._eval(v, env) for k, v in node.kwargs.items()}

        if isinstance(func, UserFunction):
            return self._call_user_function(func, args, kwargs, node.line)
        if isinstance(func, UserClass):
            return self._instantiate_class(func, args, kwargs, node.line)
        if isinstance(func, _BoundMethod):
            return self._call_user_function(func.fn, [func.instance] + args, kwargs, node.line)
        if callable(func):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise
        raise RuntimeError_(f"'{repr(func)}' is not callable", node.line)

    def _call_user_function(self, func: UserFunction, args, kwargs, line=None):
        local_env = Environment(parent=func.closure, name=func.name)
        # bind params
        param_list = func.params  # [(name, default, type_hint), ...]
        arg_idx = 0
        for i, (p_name, default, _) in enumerate(param_list):
            if arg_idx < len(args):
                local_env.set(p_name, args[arg_idx])
                arg_idx += 1
            elif p_name in kwargs:
                local_env.set(p_name, kwargs[p_name])
            elif default is not None:
                local_env.set(p_name, self._eval(default, func.closure))
            else:
                raise RuntimeError_(f"Missing argument '{p_name}' in call to '{func.name}'", line)
        try:
            self._exec_stmts(func.body, local_env)
        except ReturnSignal as rs:
            return rs.value
        return None

    def _instantiate_class(self, cls: UserClass, args, kwargs, line=None):
        instance = UserInstance(cls)
        # call __init__ if defined
        if '__init__' in cls._env:
            init_fn = cls._env['__init__']
            if isinstance(init_fn, UserFunction):
                self._call_user_function(init_fn, [instance] + args, kwargs, line)
        return instance

    def _eval_LambdaExpr(self, node: LambdaExpr, env):
        # Create a synthetic UserFunction
        params = [(p, None, None) for p in node.params]
        func = UserFunction('<lambda>', params, [ReturnStatement(node.body)], env)
        return lambda *args: self._call_user_function(func, list(args), {})

    def _eval_ListComp(self, node: ListComp, env):
        result = []
        iterable = self._eval(node.iterable, env)
        comp_env = Environment(parent=env, name='listcomp')
        for item in iterable:
            self._assign_for_target(node.target, item, comp_env)
            if node.condition is None or self._eval(node.condition, comp_env):
                result.append(self._eval(node.element, comp_env))
        return result

    def _eval_DictComp(self, node: DictComp, env):
        result = {}
        iterable = self._eval(node.iterable, env)
        comp_env = Environment(parent=env, name='dictcomp')
        for item in iterable:
            self._assign_for_target(node.target, item, comp_env)
            if node.condition is None or self._eval(node.condition, comp_env):
                k = self._eval(node.key, comp_env)
                v = self._eval(node.value, comp_env)
                result[k] = v
        return result

    def _eval_SetComp(self, node: SetComp, env):
        result = set()
        iterable = self._eval(node.iterable, env)
        comp_env = Environment(parent=env, name='setcomp')
        for item in iterable:
            self._assign_for_target(node.target, item, comp_env)
            if node.condition is None or self._eval(node.condition, comp_env):
                result.add(self._eval(node.element, comp_env))
        return result

    def _assign_for_target(self, target, value, env):
        if isinstance(target, Identifier):
            env.set(target.name, value)
        elif isinstance(target, TupleLiteral):
            for t, v in zip(target.elements, value):
                if isinstance(t, Identifier):
                    env.set(t.name, v)

    def _eval_Assignment(self, node: Assignment, env):
        """Assignment used as expression (walrus-like)."""
        value = self._eval(node.value, env)
        self._assign_target(node.target, value, env, node.line)
        return value

    @property
    def execution_history(self):
        return self._execution_history


# ─── convenience ─────────────────────────────────────────────────────────────

def run(source: str, stdout=None) -> tuple:
    """
    Compile and execute source code.
    Returns (output_str, execution_history, errors).
    """
    from lexer import tokenize
    from parser import Parser
    from semantic import SemanticAnalyzer

    errors = []
    buf = io.StringIO()
    interp = Interpreter(stdout=buf)

    try:
        tokens = tokenize(source)
        ast = Parser(tokens).parse()
        sa = SemanticAnalyzer()
        sem_errors = sa.analyze(ast)
        if sem_errors:
            for e in sem_errors:
                errors.append(str(e))
        interp.execute(ast)
    except (ZeroDivisionError, TypeError, ValueError, KeyError, IndexError,
            AttributeError, NameError, AssertionError) as e:
        errors.append(f"{type(e).__name__}: {e}")
    except Exception as e:
        errors.append(str(e))

    return buf.getvalue(), interp.execution_history, errors, (sa if 'sa' in dir() else None)


if __name__ == '__main__':
    import sys
    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    output, history, errors, sa = run(src)
    print(output, end='')
    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
