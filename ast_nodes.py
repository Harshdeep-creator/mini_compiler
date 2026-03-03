"""
ast_nodes.py - AST Node definitions for the Mini Python Compiler
Covers: variables, arithmetic, print, if, while, for, functions,
        lists, tuples, sets, dicts, strings, booleans, match, iterators, range, arrays
"""


class Node:
    """Base AST node."""
    def __init__(self, line=None):
        self.line = line

    def __repr__(self):
        return self.__class__.__name__


# ─── Literals ────────────────────────────────────────────────────────────────

class NumberLiteral(Node):
    def __init__(self, value, line=None):
        super().__init__(line)
        self.value = value

    def __repr__(self):
        return f"Number({self.value})"


class StringLiteral(Node):
    def __init__(self, value, line=None):
        super().__init__(line)
        self.value = value

    def __repr__(self):
        return f"String({repr(self.value)})"


class BoolLiteral(Node):
    def __init__(self, value, line=None):
        super().__init__(line)
        self.value = value  # True or False

    def __repr__(self):
        return f"Bool({self.value})"


class NoneLiteral(Node):
    def __init__(self, line=None):
        super().__init__(line)

    def __repr__(self):
        return "None"


# ─── Collections ─────────────────────────────────────────────────────────────

class ListLiteral(Node):
    def __init__(self, elements, line=None):
        super().__init__(line)
        self.elements = elements  # list of Nodes

    def __repr__(self):
        return f"List([{', '.join(map(repr, self.elements))}])"


class TupleLiteral(Node):
    def __init__(self, elements, line=None):
        super().__init__(line)
        self.elements = elements

    def __repr__(self):
        return f"Tuple(({', '.join(map(repr, self.elements))}))"


class SetLiteral(Node):
    def __init__(self, elements, line=None):
        super().__init__(line)
        self.elements = elements

    def __repr__(self):
        return f"Set({{{', '.join(map(repr, self.elements))}}})"


class DictLiteral(Node):
    def __init__(self, pairs, line=None):
        super().__init__(line)
        self.pairs = pairs  # list of (key_node, value_node)

    def __repr__(self):
        pairs = ', '.join(f"{repr(k)}: {repr(v)}" for k, v in self.pairs)
        return f"Dict({{{pairs}}})"


# ─── Identifiers & Access ─────────────────────────────────────────────────────

class Identifier(Node):
    def __init__(self, name, line=None):
        super().__init__(line)
        self.name = name

    def __repr__(self):
        return f"Identifier({self.name})"


class IndexAccess(Node):
    """obj[index]"""
    def __init__(self, obj, index, line=None):
        super().__init__(line)
        self.obj = obj
        self.index = index

    def __repr__(self):
        return f"Index({repr(self.obj)}[{repr(self.index)}])"


class SliceAccess(Node):
    """obj[start:stop:step]"""
    def __init__(self, obj, start, stop, step, line=None):
        super().__init__(line)
        self.obj = obj
        self.start = start
        self.stop = stop
        self.step = step

    def __repr__(self):
        return f"Slice({repr(self.obj)})"


class AttributeAccess(Node):
    """obj.attr"""
    def __init__(self, obj, attr, line=None):
        super().__init__(line)
        self.obj = obj
        self.attr = attr

    def __repr__(self):
        return f"Attr({repr(self.obj)}.{self.attr})"


# ─── Operators ────────────────────────────────────────────────────────────────

class BinaryOp(Node):
    def __init__(self, left, op, right, line=None):
        super().__init__(line)
        self.left = left
        self.op = op
        self.right = right

    def __repr__(self):
        return f"BinaryOp({repr(self.left)} {self.op} {repr(self.right)})"


class UnaryOp(Node):
    def __init__(self, op, operand, line=None):
        super().__init__(line)
        self.op = op
        self.operand = operand

    def __repr__(self):
        return f"UnaryOp({self.op}{repr(self.operand)})"


class CompareOp(Node):
    """Chained comparisons: a < b > c"""
    def __init__(self, left, ops, comparators, line=None):
        super().__init__(line)
        self.left = left
        self.ops = ops              # list of operator strings
        self.comparators = comparators  # list of nodes

    def __repr__(self):
        parts = [repr(self.left)]
        for op, comp in zip(self.ops, self.comparators):
            parts.append(op)
            parts.append(repr(comp))
        return f"Compare({' '.join(parts)})"


class BoolOp(Node):
    """and / or"""
    def __init__(self, op, values, line=None):
        super().__init__(line)
        self.op = op        # 'and' or 'or'
        self.values = values

    def __repr__(self):
        joined = f" {self.op} ".join(map(repr, self.values))
        return f"BoolOp({joined})"


# ─── Statements ───────────────────────────────────────────────────────────────

class Program(Node):
    def __init__(self, statements, line=None):
        super().__init__(line)
        self.statements = statements

    def __repr__(self):
        return f"Program({len(self.statements)} statements)"


class Assignment(Node):
    def __init__(self, target, value, type_hint=None, line=None):
        super().__init__(line)
        self.target = target    # Identifier or IndexAccess
        self.value = value
        self.type_hint = type_hint

    def __repr__(self):
        return f"Assignment({repr(self.target)} = {repr(self.value)})"


class AugAssignment(Node):
    """+=, -=, *=, /=, etc."""
    def __init__(self, target, op, value, line=None):
        super().__init__(line)
        self.target = target
        self.op = op
        self.value = value

    def __repr__(self):
        return f"AugAssign({repr(self.target)} {self.op}= {repr(self.value)})"


class MultiAssignment(Node):
    """a, b = 1, 2  (tuple unpacking)"""
    def __init__(self, targets, value, line=None):
        super().__init__(line)
        self.targets = targets
        self.value = value

    def __repr__(self):
        return f"MultiAssign({', '.join(map(repr, self.targets))} = {repr(self.value)})"


class PrintStatement(Node):
    def __init__(self, args, sep=' ', end='\n', line=None):
        super().__init__(line)
        self.args = args
        self.sep = sep
        self.end = end

    def __repr__(self):
        return f"Print({', '.join(map(repr, self.args))})"


class IfStatement(Node):
    def __init__(self, condition, body, elif_clauses=None, else_body=None, line=None):
        super().__init__(line)
        self.condition = condition
        self.body = body                        # list of statements
        self.elif_clauses = elif_clauses or []  # list of (condition, body)
        self.else_body = else_body or []

    def __repr__(self):
        return f"If({repr(self.condition)})"


class WhileStatement(Node):
    def __init__(self, condition, body, else_body=None, line=None):
        super().__init__(line)
        self.condition = condition
        self.body = body
        self.else_body = else_body or []

    def __repr__(self):
        return f"While({repr(self.condition)})"


class ForStatement(Node):
    def __init__(self, target, iterable, body, else_body=None, line=None):
        super().__init__(line)
        self.target = target        # Identifier or tuple of Identifiers
        self.iterable = iterable
        self.body = body
        self.else_body = else_body or []

    def __repr__(self):
        return f"For({repr(self.target)} in {repr(self.iterable)})"


class MatchStatement(Node):
    def __init__(self, subject, cases, line=None):
        super().__init__(line)
        self.subject = subject
        self.cases = cases  # list of (pattern, guard, body)

    def __repr__(self):
        return f"Match({repr(self.subject)})"


class BreakStatement(Node):
    def __repr__(self):
        return "Break"


class ContinueStatement(Node):
    def __repr__(self):
        return "Continue"


class PassStatement(Node):
    def __repr__(self):
        return "Pass"


class ReturnStatement(Node):
    def __init__(self, value=None, line=None):
        super().__init__(line)
        self.value = value

    def __repr__(self):
        return f"Return({repr(self.value)})"


class DeleteStatement(Node):
    def __init__(self, target, line=None):
        super().__init__(line)
        self.target = target

    def __repr__(self):
        return f"Del({repr(self.target)})"


# ─── Functions & Classes ──────────────────────────────────────────────────────

class FunctionDef(Node):
    def __init__(self, name, params, body, return_type=None, line=None):
        super().__init__(line)
        self.name = name
        self.params = params        # list of (name, default_value, type_hint)
        self.body = body
        self.return_type = return_type

    def __repr__(self):
        return f"FunctionDef({self.name})"


class LambdaExpr(Node):
    def __init__(self, params, body, line=None):
        super().__init__(line)
        self.params = params
        self.body = body

    def __repr__(self):
        return f"Lambda({', '.join(self.params)})"


class FunctionCall(Node):
    def __init__(self, func, args, kwargs=None, line=None):
        super().__init__(line)
        self.func = func            # Node (Identifier or AttributeAccess)
        self.args = args
        self.kwargs = kwargs or {}

    def __repr__(self):
        return f"Call({repr(self.func)}({', '.join(map(repr, self.args))}))"


class ClassDef(Node):
    def __init__(self, name, bases, body, line=None):
        super().__init__(line)
        self.name = name
        self.bases = bases
        self.body = body

    def __repr__(self):
        return f"ClassDef({self.name})"


# ─── Comprehensions ───────────────────────────────────────────────────────────

class ListComp(Node):
    def __init__(self, element, target, iterable, condition=None, line=None):
        super().__init__(line)
        self.element = element
        self.target = target
        self.iterable = iterable
        self.condition = condition

    def __repr__(self):
        return f"ListComp({repr(self.element)} for {repr(self.target)} in {repr(self.iterable)})"


class DictComp(Node):
    def __init__(self, key, value, target, iterable, condition=None, line=None):
        super().__init__(line)
        self.key = key
        self.value = value
        self.target = target
        self.iterable = iterable
        self.condition = condition

    def __repr__(self):
        return f"DictComp({repr(self.key)}: {repr(self.value)} for ...)"


class SetComp(Node):
    def __init__(self, element, target, iterable, condition=None, line=None):
        super().__init__(line)
        self.element = element
        self.target = target
        self.iterable = iterable
        self.condition = condition

    def __repr__(self):
        return f"SetComp({repr(self.element)} for ...)"


# ─── Special Expressions ──────────────────────────────────────────────────────

class TernaryOp(Node):
    """value_if_true if condition else value_if_false"""
    def __init__(self, condition, true_val, false_val, line=None):
        super().__init__(line)
        self.condition = condition
        self.true_val = true_val
        self.false_val = false_val

    def __repr__(self):
        return f"Ternary({repr(self.true_val)} if {repr(self.condition)} else {repr(self.false_val)})"


class InOperator(Node):
    """x in collection  /  x not in collection"""
    def __init__(self, element, collection, negated=False, line=None):
        super().__init__(line)
        self.element = element
        self.collection = collection
        self.negated = negated

    def __repr__(self):
        op = "not in" if self.negated else "in"
        return f"In({repr(self.element)} {op} {repr(self.collection)})"


class IsOperator(Node):
    """x is y  /  x is not y"""
    def __init__(self, left, right, negated=False, line=None):
        super().__init__(line)
        self.left = left
        self.right = right
        self.negated = negated

    def __repr__(self):
        op = "is not" if self.negated else "is"
        return f"Is({repr(self.left)} {op} {repr(self.right)})"


class ExprStatement(Node):
    """A standalone expression used as a statement (e.g., function call)."""
    def __init__(self, expr, line=None):
        super().__init__(line)
        self.expr = expr

    def __repr__(self):
        return f"Expr({repr(self.expr)})"


class ImportStatement(Node):
    def __init__(self, module, alias=None, line=None):
        super().__init__(line)
        self.module = module
        self.alias = alias

    def __repr__(self):
        return f"Import({self.module})"


class FromImport(Node):
    def __init__(self, module, names, line=None):
        super().__init__(line)
        self.module = module
        self.names = names  # list of (name, alias)

    def __repr__(self):
        return f"FromImport({self.module})"


class GlobalStatement(Node):
    def __init__(self, names, line=None):
        super().__init__(line)
        self.names = names

    def __repr__(self):
        return f"Global({', '.join(self.names)})"


class AssertStatement(Node):
    def __init__(self, condition, message=None, line=None):
        super().__init__(line)
        self.condition = condition
        self.message = message

    def __repr__(self):
        return f"Assert({repr(self.condition)})"


class RaiseStatement(Node):
    def __init__(self, exception=None, line=None):
        super().__init__(line)
        self.exception = exception

    def __repr__(self):
        return f"Raise({repr(self.exception)})"


class TryStatement(Node):
    def __init__(self, body, handlers, else_body=None, finally_body=None, line=None):
        super().__init__(line)
        self.body = body
        self.handlers = handlers   # list of (exc_type, name, body)
        self.else_body = else_body or []
        self.finally_body = finally_body or []

    def __repr__(self):
        return "Try(...)"


class WithStatement(Node):
    def __init__(self, context_expr, target, body, line=None):
        super().__init__(line)
        self.context_expr = context_expr
        self.target = target
        self.body = body

    def __repr__(self):
        return f"With({repr(self.context_expr)})"
