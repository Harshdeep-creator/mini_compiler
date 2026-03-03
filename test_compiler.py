"""
tests/test_compiler.py - Full test suite for the Mini Python Compiler
"""

import sys
import os
import io
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from lexer import tokenize, Token
from parser import parse
from semantic import SemanticAnalyzer
from interpreter import Interpreter, run
from errors import LexerError, ParseError


def execute(code: str) -> str:
    """Helper: run code and return stdout as string."""
    output, _, errors, _ = run(code)
    if errors:
        raise AssertionError(f"Unexpected errors: {errors}")
    return output.strip()


# ─── Lexer Tests ─────────────────────────────────────────────────────────────

class TestLexer(unittest.TestCase):

    def _types(self, code):
        return [t.type for t in tokenize(code) if t.type not in ('NEWLINE','INDENT','DEDENT','EOF')]

    def test_integers(self):
        tokens = [t for t in tokenize("42 0xFF 0b101") if t.type not in ('NEWLINE','INDENT','DEDENT','EOF')]
        self.assertEqual(tokens[0].value, 42)
        self.assertEqual(tokens[1].value, 255)
        self.assertEqual(tokens[2].value, 5)

    def test_floats(self):
        tokens = [t for t in tokenize("3.14 .5 2.") if t.type not in ('NEWLINE','INDENT','DEDENT','EOF')]
        self.assertAlmostEqual(tokens[0].value, 3.14)
        self.assertAlmostEqual(tokens[1].value, 0.5)

    def test_strings(self):
        tokens = [t for t in tokenize('"hello"') if t.type == 'STRING']
        self.assertEqual(tokens[0].value, 'hello')

    def test_booleans(self):
        types = self._types("True False")
        self.assertIn('TRUE', types)
        self.assertIn('FALSE', types)

    def test_keywords(self):
        code = "if elif else while for def return break continue pass"
        types = self._types(code)
        self.assertIn('IF', types)
        self.assertIn('WHILE', types)
        self.assertIn('DEF', types)

    def test_operators(self):
        types = self._types("+ - * / // % ** == != <= >= < >")
        self.assertIn('PLUS', types)
        self.assertIn('POWER', types)
        self.assertIn('EQ', types)
        self.assertIn('FLOOR_DIV', types)

    def test_comment_ignored(self):
        types = self._types("x = 5  # this is a comment")
        self.assertNotIn('COMMENT', types)

    def test_aug_assign(self):
        types = self._types("+= -= *= /=")
        self.assertEqual(types.count('AUG_ASSIGN'), 4)

    def test_line_tracking(self):
        tokens = [t for t in tokenize("x\ny") if t.type == 'NAME']
        self.assertEqual(tokens[0].line, 1)
        self.assertEqual(tokens[1].line, 2)


# ─── Parser Tests ─────────────────────────────────────────────────────────────

class TestParser(unittest.TestCase):

    def test_assignment(self):
        from ast_nodes import Program, Assignment
        tree = parse("x = 42")
        self.assertIsInstance(tree, Program)
        self.assertIsInstance(tree.statements[0], Assignment)

    def test_type_annotated(self):
        from ast_nodes import Assignment
        tree = parse("x: int = 5")
        stmt = tree.statements[0]
        self.assertIsInstance(stmt, Assignment)
        self.assertEqual(stmt.type_hint, 'int')

    def test_binary_op(self):
        from ast_nodes import ExprStatement, BinaryOp
        tree = parse("3 + 4 * 2")
        expr = tree.statements[0].expr
        self.assertIsInstance(expr, BinaryOp)

    def test_function_def(self):
        from ast_nodes import FunctionDef
        tree = parse("def foo(a, b):\n    return a + b\n")
        self.assertIsInstance(tree.statements[0], FunctionDef)
        self.assertEqual(tree.statements[0].name, 'foo')

    def test_if_elif_else(self):
        from ast_nodes import IfStatement
        code = "if x > 0:\n    pass\nelif x < 0:\n    pass\nelse:\n    pass\n"
        tree = parse(code)
        stmt = tree.statements[0]
        self.assertIsInstance(stmt, IfStatement)
        self.assertEqual(len(stmt.elif_clauses), 1)
        self.assertTrue(len(stmt.else_body) > 0)

    def test_for_loop(self):
        from ast_nodes import ForStatement
        tree = parse("for i in range(10):\n    pass\n")
        self.assertIsInstance(tree.statements[0], ForStatement)

    def test_list_literal(self):
        from ast_nodes import ExprStatement, ListLiteral
        tree = parse("[1, 2, 3]")
        expr = tree.statements[0].expr
        self.assertIsInstance(expr, ListLiteral)
        self.assertEqual(len(expr.elements), 3)

    def test_dict_literal(self):
        from ast_nodes import ExprStatement, DictLiteral
        tree = parse('{"a": 1, "b": 2}')
        expr = tree.statements[0].expr
        self.assertIsInstance(expr, DictLiteral)

    def test_list_comprehension(self):
        from ast_nodes import ExprStatement, ListComp
        tree = parse("[x*2 for x in range(5)]")
        expr = tree.statements[0].expr
        self.assertIsInstance(expr, ListComp)

    def test_lambda(self):
        from ast_nodes import Assignment, LambdaExpr
        tree = parse("f = lambda x: x * 2")
        self.assertIsInstance(tree.statements[0].value, LambdaExpr)

    def test_ternary(self):
        from ast_nodes import ExprStatement, TernaryOp
        tree = parse("1 if True else 2")
        expr = tree.statements[0].expr
        self.assertIsInstance(expr, TernaryOp)

    def test_class_def(self):
        from ast_nodes import ClassDef
        tree = parse("class Foo:\n    pass\n")
        self.assertIsInstance(tree.statements[0], ClassDef)

    def test_match(self):
        from ast_nodes import MatchStatement
        code = "match x:\n    case 1:\n        pass\n"
        tree = parse(code)
        self.assertIsInstance(tree.statements[0], MatchStatement)


# ─── Semantic Tests ───────────────────────────────────────────────────────────

class TestSemantic(unittest.TestCase):

    def _analyze(self, code):
        tree = parse(code)
        sa = SemanticAnalyzer()
        errors = sa.analyze(tree)
        return sa, errors

    def test_undefined_variable(self):
        _, errors = self._analyze("print(z)")
        self.assertTrue(any("z" in str(e) for e in errors))

    def test_defined_variable(self):
        _, errors = self._analyze("x = 5\nprint(x)")
        self.assertEqual(errors, [])

    def test_function_redeclaration_warning(self):
        sa, _ = self._analyze("def foo():\n    pass\ndef foo():\n    pass\n")
        self.assertTrue(any("foo" in w for w in sa.warnings))

    def test_return_outside_function(self):
        _, errors = self._analyze("return 5")
        self.assertTrue(any("return" in str(e).lower() for e in errors))

    def test_break_outside_loop(self):
        _, errors = self._analyze("break")
        self.assertTrue(any("break" in str(e).lower() for e in errors))

    def test_function_params_defined(self):
        _, errors = self._analyze("def foo(a, b):\n    return a + b\n")
        self.assertEqual(errors, [])

    def test_snapshot_recorded(self):
        sa, _ = self._analyze("x = 5\ny = 10\n")
        self.assertTrue(len(sa.snapshots) > 0)


# ─── Interpreter Tests ────────────────────────────────────────────────────────

class TestInterpreter(unittest.TestCase):

    # ── arithmetic ────────────────────────────────────────────────────────────
    def test_add(self):        self.assertEqual(execute("print(2 + 3)"), "5")
    def test_subtract(self):   self.assertEqual(execute("print(10 - 4)"), "6")
    def test_multiply(self):   self.assertEqual(execute("print(3 * 4)"), "12")
    def test_divide(self):     self.assertEqual(execute("print(10 / 4)"), "2.5")
    def test_floor_div(self):  self.assertEqual(execute("print(10 // 3)"), "3")
    def test_modulo(self):     self.assertEqual(execute("print(10 % 3)"), "1")
    def test_power(self):      self.assertEqual(execute("print(2 ** 8)"), "256")

    # ── variables ────────────────────────────────────────────────────────────
    def test_variable(self):
        self.assertEqual(execute("x = 42\nprint(x)"), "42")

    def test_type_hint(self):
        self.assertEqual(execute("x: int = 99\nprint(x)"), "99")

    def test_augmented_assign(self):
        self.assertEqual(execute("x = 5\nx += 3\nprint(x)"), "8")

    def test_multi_assign(self):
        self.assertEqual(execute("a, b = 1, 2\nprint(a, b)"), "1 2")

    # ── strings ──────────────────────────────────────────────────────────────
    def test_string_concat(self):
        self.assertEqual(execute('print("Hello" + " " + "World")'), "Hello World")

    def test_string_repeat(self):
        self.assertEqual(execute('print("ab" * 3)'), "ababab")

    def test_string_slice(self):
        self.assertEqual(execute('s = "Hello"\nprint(s[1:4])'), "ell")

    def test_string_upper(self):
        self.assertEqual(execute('print("hello".upper())'), "HELLO")

    def test_string_len(self):
        self.assertEqual(execute('print(len("Hello"))'), "5")

    def test_string_replace(self):
        self.assertEqual(execute('print("hello".replace("hello", "world"))'), "world")

    def test_string_split(self):
        self.assertEqual(execute('print("a,b,c".split(","))'), "['a', 'b', 'c']")

    # ── booleans ─────────────────────────────────────────────────────────────
    def test_bool_and(self):
        self.assertEqual(execute("print(True and False)"), "False")

    def test_bool_or(self):
        self.assertEqual(execute("print(True or False)"), "True")

    def test_bool_not(self):
        self.assertEqual(execute("print(not True)"), "False")

    # ── comparisons ──────────────────────────────────────────────────────────
    def test_compare_lt(self):
        self.assertEqual(execute("print(3 < 5)"), "True")

    def test_compare_eq(self):
        self.assertEqual(execute("print(5 == 5)"), "True")

    def test_compare_ne(self):
        self.assertEqual(execute("print(3 != 5)"), "True")

    # ── if/elif/else ─────────────────────────────────────────────────────────
    def test_if_true(self):
        self.assertEqual(execute("if True:\n    print('yes')\n"), "yes")

    def test_if_false(self):
        self.assertEqual(execute("if False:\n    print('yes')\nelse:\n    print('no')\n"), "no")

    def test_elif(self):
        code = "x=5\nif x>10:\n    print('big')\nelif x>3:\n    print('mid')\nelse:\n    print('small')\n"
        self.assertEqual(execute(code), "mid")

    # ── while ─────────────────────────────────────────────────────────────────
    def test_while(self):
        self.assertEqual(execute("i=0\nwhile i<3:\n    i+=1\nprint(i)"), "3")

    def test_while_break(self):
        code = "i=0\nwhile True:\n    if i==3:\n        break\n    i+=1\nprint(i)\n"
        self.assertEqual(execute(code), "3")

    # ── for ───────────────────────────────────────────────────────────────────
    def test_for_range(self):
        self.assertEqual(execute("s=0\nfor i in range(5):\n    s+=i\nprint(s)"), "10")

    def test_for_list(self):
        self.assertEqual(execute("for x in [1,2,3]:\n    print(x)\n"), "1\n2\n3")

    def test_for_continue(self):
        code = "for i in range(5):\n    if i==2:\n        continue\n    print(i)\n"
        self.assertEqual(execute(code), "0\n1\n3\n4")

    # ── functions ─────────────────────────────────────────────────────────────
    def test_function_basic(self):
        self.assertEqual(execute("def add(a,b):\n    return a+b\nprint(add(3,4))"), "7")

    def test_function_default_param(self):
        code = "def greet(name, msg='Hi'):\n    return msg + ' ' + name\nprint(greet('Alice'))\n"
        self.assertEqual(execute(code), "Hi Alice")

    def test_recursive(self):
        code = "def fib(n):\n    if n<=1:\n        return n\n    return fib(n-1)+fib(n-2)\nprint(fib(10))\n"
        self.assertEqual(execute(code), "55")

    def test_function_no_return(self):
        code = "def foo():\n    x=1\nresult = foo()\nprint(result)\n"
        self.assertEqual(execute(code), "None")

    # ── lists ─────────────────────────────────────────────────────────────────
    def test_list_literal(self):
        self.assertEqual(execute("print([1,2,3])"), "[1, 2, 3]")

    def test_list_append(self):
        self.assertEqual(execute("a=[1,2]\na.append(3)\nprint(a)"), "[1, 2, 3]")

    def test_list_index(self):
        self.assertEqual(execute("a=[10,20,30]\nprint(a[1])"), "20")

    def test_list_slice(self):
        self.assertEqual(execute("a=[1,2,3,4,5]\nprint(a[1:4])"), "[2, 3, 4]")

    def test_list_len(self):
        self.assertEqual(execute("print(len([1,2,3,4]))"), "4")

    def test_list_in(self):
        self.assertEqual(execute("print(2 in [1,2,3])"), "True")

    def test_list_comp(self):
        self.assertEqual(execute("print([x**2 for x in range(4)])"), "[0, 1, 4, 9]")

    def test_list_sort(self):
        self.assertEqual(execute("a=[3,1,4,1,5]\na.sort()\nprint(a)"), "[1, 1, 3, 4, 5]")

    # ── tuples ────────────────────────────────────────────────────────────────
    def test_tuple_literal(self):
        self.assertEqual(execute("t=(1,2,3)\nprint(t)"), "(1, 2, 3)")

    def test_tuple_unpack(self):
        self.assertEqual(execute("a,b,c=(1,2,3)\nprint(a,b,c)"), "1 2 3")

    def test_tuple_index(self):
        self.assertEqual(execute("t=(10,20,30)\nprint(t[2])"), "30")

    # ── sets ──────────────────────────────────────────────────────────────────
    def test_set_literal(self):
        result = execute("s={1,2,3}\nprint(len(s))")
        self.assertEqual(result, "3")

    def test_set_add(self):
        self.assertEqual(execute("s={1,2}\ns.add(3)\nprint(len(s))"), "3")

    def test_set_in(self):
        self.assertEqual(execute("s={1,2,3}\nprint(2 in s)"), "True")

    # ── dicts ─────────────────────────────────────────────────────────────────
    def test_dict_literal(self):
        self.assertEqual(execute('d={"a":1}\nprint(d["a"])'), "1")

    def test_dict_set(self):
        self.assertEqual(execute('d={}\nd["x"]=99\nprint(d["x"])'), "99")

    def test_dict_keys(self):
        result = execute('d={"a":1,"b":2}\nprint(len(d))') 
        self.assertEqual(result, "2")

    def test_dict_get(self):
        self.assertEqual(execute('d={"a":1}\nprint(d.get("b", 0))'), "0")

    def test_dict_in(self):
        self.assertEqual(execute('d={"a":1}\nprint("a" in d)'), "True")

    # ── range & iterators ─────────────────────────────────────────────────────
    def test_range_basic(self):
        self.assertEqual(execute("print(list(range(5)))"), "[0, 1, 2, 3, 4]")

    def test_range_start_stop(self):
        self.assertEqual(execute("print(list(range(2,6)))"), "[2, 3, 4, 5]")

    def test_range_step(self):
        self.assertEqual(execute("print(list(range(0,10,2)))"), "[0, 2, 4, 6, 8]")

    def test_enumerate(self):
        result = execute("for i,v in enumerate(['a','b']):\n    print(i,v)\n")
        self.assertEqual(result, "0 a\n1 b")

    def test_zip(self):
        result = execute("for a,b in zip([1,2],[3,4]):\n    print(a,b)\n")
        self.assertEqual(result, "1 3\n2 4")

    def test_iter_next(self):
        result = execute("it=iter([10,20,30])\nprint(next(it))\nprint(next(it))")
        self.assertEqual(result, "10\n20")

    # ── match/case ────────────────────────────────────────────────────────────
    def test_match_literal(self):
        code = "x=2\nmatch x:\n    case 1:\n        print('one')\n    case 2:\n        print('two')\n    case _:\n        print('other')\n"
        self.assertEqual(execute(code), "two")

    def test_match_wildcard(self):
        code = "x=99\nmatch x:\n    case 1:\n        print('one')\n    case _:\n        print('other')\n"
        self.assertEqual(execute(code), "other")

    # ── lambda ────────────────────────────────────────────────────────────────
    def test_lambda_basic(self):
        self.assertEqual(execute("f = lambda x: x * 2\nprint(f(5))"), "10")

    def test_lambda_map(self):
        self.assertEqual(execute("print(list(map(lambda x: x+1, [1,2,3])))"), "[2, 3, 4]")

    def test_lambda_filter(self):
        self.assertEqual(execute("print(list(filter(lambda x: x>2, [1,2,3,4])))"), "[3, 4]")

    # ── classes ───────────────────────────────────────────────────────────────
    def test_class_basic(self):
        code = "class Dog:\n    def __init__(self, name):\n        self.name = name\n    def bark(self):\n        return self.name + ' says woof'\nd = Dog('Rex')\nprint(d.bark())\n"
        self.assertEqual(execute(code), "Rex says woof")

    # ── try/except ────────────────────────────────────────────────────────────
    def test_try_except(self):
        code = "try:\n    x = 1/0\nexcept ZeroDivisionError:\n    print('caught')\n"
        self.assertEqual(execute(code), "caught")

    def test_try_else(self):
        code = "try:\n    x = 1\nexcept:\n    print('error')\nelse:\n    print('ok')\n"
        self.assertEqual(execute(code), "ok")

    # ── builtins ──────────────────────────────────────────────────────────────
    def test_abs(self):       self.assertEqual(execute("print(abs(-5))"), "5")
    def test_max(self):       self.assertEqual(execute("print(max(1,2,3))"), "3")
    def test_min(self):       self.assertEqual(execute("print(min(1,2,3))"), "1")
    def test_sum(self):       self.assertEqual(execute("print(sum([1,2,3,4]))"), "10")
    def test_round(self):     self.assertEqual(execute("print(round(3.7))"), "4")
    def test_sorted(self):    self.assertEqual(execute("print(sorted([3,1,2]))"), "[1, 2, 3]")
    def test_reversed(self):  self.assertEqual(execute("print(list(reversed([1,2,3])))"), "[3, 2, 1]")
    def test_int_cast(self):  self.assertEqual(execute("print(int('42'))"), "42")
    def test_float_cast(self):self.assertEqual(execute("print(float('3.14'))"), "3.14")
    def test_str_cast(self):  self.assertEqual(execute("print(str(42))"), "42")
    def test_bool_cast(self): self.assertEqual(execute("print(bool(0))"), "False")
    def test_type_fn(self):   self.assertEqual(execute("print(type(42))"), "int")
    def test_chr(self):       self.assertEqual(execute("print(chr(65))"), "A")
    def test_ord(self):       self.assertEqual(execute("print(ord('A'))"), "65")
    def test_hex(self):       self.assertEqual(execute("print(hex(255))"), "0xff")
    def test_bin(self):       self.assertEqual(execute("print(bin(5))"), "0b101")
    def test_pow(self):       self.assertEqual(execute("print(pow(2,10))"), "1024")
    def test_any(self):       self.assertEqual(execute("print(any([False,True,False]))"), "True")
    def test_all(self):       self.assertEqual(execute("print(all([True,True,True]))"), "True")
    def test_isinstance(self):self.assertEqual(execute("print(isinstance(5, int))"), "True")

    # ── arrays (lists used as arrays) ─────────────────────────────────────────
    def test_2d_array(self):
        code = "m=[[0]*3 for _ in range(3)]\nm[1][1]=99\nprint(m[1][1])\n"
        self.assertEqual(execute(code), "99")

    # ── global ────────────────────────────────────────────────────────────────
    def test_global(self):
        code = "x=0\ndef inc():\n    global x\n    x+=1\ninc()\ninc()\nprint(x)\n"
        self.assertEqual(execute(code), "2")

    # ── nested functions ──────────────────────────────────────────────────────
    def test_nested_functions(self):
        code = ("def outer(x):\n"
                "    def inner(y):\n"
                "        return x + y\n"
                "    return inner(10)\n"
                "print(outer(5))\n")
        self.assertEqual(execute(code), "15")

    # ── ternary ───────────────────────────────────────────────────────────────
    def test_ternary(self):
        self.assertEqual(execute("x=10\nprint('big' if x>5 else 'small')"), "big")

    # ── chained comparisons ───────────────────────────────────────────────────
    def test_chained_compare(self):
        self.assertEqual(execute("print(1 < 2 < 3)"), "True")
        self.assertEqual(execute("print(1 < 2 > 5)"), "False")


# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    unittest.main(verbosity=2)
