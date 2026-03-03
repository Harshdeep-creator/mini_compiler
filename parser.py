"""
parser.py - Recursive-descent parser for the Mini Python Compiler

Consumes a token stream (from lexer.py) and produces an AST (ast_nodes.py).
Supports: assignments, type hints, augmented assignments, arithmetic, booleans,
          comparisons, if/elif/else, while, for, match/case, functions, classes,
          lists, tuples, sets, dicts, comprehensions, lambdas, slices, try/except,
          with, import, global, assert, raise, del, break, continue, pass, return,
          print (as statement *and* built-in call), range, iterators, ternary.
"""

from lexer import tokenize, Token
from ast_nodes import *
from errors import ParseError


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = [t for t in tokens if t.type not in ('NEWLINE', 'INDENT', 'DEDENT')]
        # We preserve INDENT/DEDENT for block parsing — keep them in a separate pass
        self._raw_tokens = tokens
        self._pos = 0
        # We'll use raw tokens for block-aware parsing
        self._raw_pos = 0

    # ─── token helpers ────────────────────────────────────────────────────────

    def _raw_peek(self, offset=0):
        i = self._raw_pos + offset
        return self._raw_tokens[i] if i < len(self._raw_tokens) else Token('EOF', '', 0, 0)

    def _raw_advance(self):
        tok = self._raw_tokens[self._raw_pos]
        self._raw_pos += 1
        return tok

    def _raw_skip_newlines(self):
        while self._raw_peek().type in ('NEWLINE',):
            self._raw_advance()

    # ── flat-token helpers (for expressions, no indent awareness) ────────────

    def _peek(self, offset=0):
        # walk raw tokens ignoring INDENT/DEDENT for expression parsing
        # but DO respect NEWLINEs as token separators (stop at them)
        skipped = 0
        i = self._raw_pos
        while True:
            if i >= len(self._raw_tokens):
                return Token('EOF', '', 0, 0)
            t = self._raw_tokens[i]
            if t.type in ('INDENT', 'DEDENT'):
                i += 1
                continue
            if skipped == offset:
                return t
            skipped += 1
            i += 1

    def _advance(self):
        """Advance raw pos past INDENT/DEDENT, return the real token."""
        while self._raw_pos < len(self._raw_tokens):
            t = self._raw_tokens[self._raw_pos]
            self._raw_pos += 1
            if t.type not in ('INDENT', 'DEDENT'):
                return t
        return Token('EOF', '', 0, 0)

    def _expect(self, type_: str, value=None):
        tok = self._advance()
        if tok.type != type_:
            raise ParseError(
                f"Expected {type_!r} but got {tok.type!r} ({repr(tok.value)})",
                tok.line, tok.col
            )
        if value is not None and tok.value != value:
            raise ParseError(
                f"Expected {repr(value)} but got {repr(tok.value)}",
                tok.line, tok.col
            )
        return tok

    def _match(self, *types):
        if self._peek().type in types:
            return self._advance()
        return None

    def _check(self, *types):
        return self._peek().type in types

    def _check_value(self, type_, value):
        t = self._peek()
        return t.type == type_ and t.value == value

    # ─── top-level ────────────────────────────────────────────────────────────

    def parse(self) -> Program:
        stmts = []
        self._skip_ws_raw()
        while not self._check('EOF'):
            s = self._parse_statement()
            if s is not None:
                stmts.append(s)
            self._skip_ws_raw()
        return Program(stmts)

    def _skip_ws_raw(self):
        """Skip NEWLINE, INDENT, DEDENT at top level."""
        while self._raw_pos < len(self._raw_tokens) and \
              self._raw_tokens[self._raw_pos].type in ('NEWLINE', 'INDENT', 'DEDENT'):
            self._raw_pos += 1

    def _skip_newlines_raw(self):
        """Skip only NEWLINE tokens, NOT INDENT/DEDENT."""
        while self._raw_pos < len(self._raw_tokens) and \
              self._raw_tokens[self._raw_pos].type == 'NEWLINE':
            self._raw_pos += 1

    # ─── statements ───────────────────────────────────────────────────────────

    def _parse_statement(self):
        tok = self._peek()
        t = tok.type

        if t == 'IF':        return self._parse_if()
        if t == 'WHILE':     return self._parse_while()
        if t == 'FOR':       return self._parse_for()
        if t == 'DEF':       return self._parse_funcdef()
        if t == 'CLASS':     return self._parse_classdef()
        if t == 'RETURN':    return self._parse_return()
        if t == 'BREAK':     self._advance(); return BreakStatement(line=tok.line)
        if t == 'CONTINUE':  self._advance(); return ContinueStatement(line=tok.line)
        if t == 'PASS':      self._advance(); return PassStatement(line=tok.line)
        if t == 'PRINT':     return self._parse_print()
        if t == 'IMPORT':    return self._parse_import()
        if t == 'FROM':      return self._parse_from_import()
        if t == 'GLOBAL':    return self._parse_global()
        if t == 'DEL':       return self._parse_del()
        if t == 'ASSERT':    return self._parse_assert()
        if t == 'RAISE':     return self._parse_raise()
        if t == 'TRY':       return self._parse_try()
        if t == 'WITH':      return self._parse_with()
        if t == 'MATCH':     return self._parse_match()

        return self._parse_expr_or_assign()

    def _parse_expr_or_assign(self):
        """Handle assignments, augmented assignments, type-annotated assignments, or bare expressions."""
        line = self._peek().line
        expr = self._parse_expression()

        # handle  a, b, c = ...  (tuple unpacking on LHS)
        if self._check('COMMA'):
            targets = [expr]
            while self._check('COMMA'):
                self._advance()
                targets.append(self._parse_expression())
            self._expect('ASSIGN')
            value = self._parse_expression()
            # collect more comma values for RHS tuple
            rhs_items = [value]
            while self._check('COMMA'):
                self._advance()
                rhs_items.append(self._parse_expression())
            self._consume_stmt_end()
            rhs = TupleLiteral(rhs_items, line=line) if len(rhs_items) > 1 else rhs_items[0]
            return MultiAssignment(targets, rhs, line=line)

        # check for augmented assignment: +=  -=  etc.
        if self._check('AUG_ASSIGN'):
            op_tok = self._advance()
            op = op_tok.value[:-1]  # strip '='
            value = self._parse_expression()
            self._consume_stmt_end()
            return AugAssignment(expr, op, value, line=line)

        # check for walrus (already consumed in expression) – shouldn't reach here

        # regular = assignment (may be chained: a = b = expr)
        if self._check('ASSIGN'):
            # could be multi-target: a, b = ...
            targets = [expr]
            while self._check('ASSIGN'):
                self._advance()
                next_expr = self._parse_expression()
                targets.append(next_expr)
            # last target is the value
            value = targets.pop()
            self._consume_stmt_end()
            if len(targets) == 1:
                target = targets[0]
                # type-annotated: x: int = 5
                type_hint = None
                # (type hints handled separately in COLON path below)
                if isinstance(target, Identifier):
                    return Assignment(target, value, line=line)
                elif isinstance(target, (IndexAccess, AttributeAccess)):
                    return Assignment(target, value, line=line)
                elif isinstance(target, TupleLiteral):
                    return MultiAssignment(target.elements, value, line=line)
                else:
                    return Assignment(target, value, line=line)
            else:
                # multiple targets: a = b = val
                stmts = []
                for t in targets:
                    stmts.append(Assignment(t, value, line=line))
                return stmts[0] if len(stmts) == 1 else stmts

        # type annotation: x: int  or  x: int = 5
        if self._check('COLON') and isinstance(expr, Identifier):
            self._advance()  # consume ':'
            type_hint = self._parse_type_hint()
            value = None
            if self._check('ASSIGN'):
                self._advance()
                value = self._parse_expression()
            self._consume_stmt_end()
            if value is not None:
                return Assignment(expr, value, type_hint=type_hint, line=line)
            # bare annotation – treat as pass
            return PassStatement(line=line)

        self._consume_stmt_end()
        return ExprStatement(expr, line=line)

    def _parse_type_hint(self):
        """Parse a type hint (simple or complex like List[int])."""
        tok = self._advance()
        name = tok.value
        if self._check('LBRACKET'):
            self._advance()
            inner = self._parse_type_hint()
            self._expect('RBRACKET')
            return f"{name}[{inner}]"
        return name

    def _consume_stmt_end(self):
        """Consume optional semicolons / newlines at end of statement."""
        while self._raw_pos < len(self._raw_tokens) and \
              self._raw_tokens[self._raw_pos].type in ('NEWLINE', 'SEMICOLON'):
            self._raw_pos += 1

    # ─── compound statements ──────────────────────────────────────────────────

    def _parse_block(self):
        """Parse an indented block of statements."""
        # skip newlines before the indent
        while self._raw_pos < len(self._raw_tokens) and \
              self._raw_tokens[self._raw_pos].type == 'NEWLINE':
            self._raw_pos += 1

        # expect INDENT
        if self._raw_pos < len(self._raw_tokens) and \
           self._raw_tokens[self._raw_pos].type == 'INDENT':
            self._raw_pos += 1  # consume INDENT
        else:
            raise ParseError("Expected indented block", self._peek().line)

        stmts = []
        while True:
            # skip blank lines
            while self._raw_pos < len(self._raw_tokens) and \
                  self._raw_tokens[self._raw_pos].type == 'NEWLINE':
                self._raw_pos += 1

            if self._raw_pos >= len(self._raw_tokens):
                break
            rt = self._raw_tokens[self._raw_pos].type
            if rt == 'DEDENT':
                self._raw_pos += 1
                break
            if rt == 'EOF':
                break
            s = self._parse_statement()
            if s is not None:
                if isinstance(s, list):
                    stmts.extend(s)
                else:
                    stmts.append(s)
        return stmts

    def _parse_if(self):
        line = self._peek().line
        self._expect('IF')
        condition = self._parse_expression()
        self._expect('COLON')
        body = self._parse_block()

        elif_clauses = []
        else_body = []

        while True:
            self._skip_newlines_raw()
            if self._check('ELIF'):
                self._advance()
                elif_cond = self._parse_expression()
                self._expect('COLON')
                elif_body = self._parse_block()
                elif_clauses.append((elif_cond, elif_body))
            elif self._check('ELSE'):
                self._advance()
                self._expect('COLON')
                else_body = self._parse_block()
                break
            else:
                break

        return IfStatement(condition, body, elif_clauses, else_body, line=line)

    def _parse_while(self):
        line = self._peek().line
        self._expect('WHILE')
        condition = self._parse_expression()
        self._expect('COLON')
        body = self._parse_block()
        else_body = []
        self._skip_newlines_raw()
        if self._check('ELSE'):
            self._advance()
            self._expect('COLON')
            else_body = self._parse_block()
        return WhileStatement(condition, body, else_body, line=line)

    def _parse_for(self):
        line = self._peek().line
        self._expect('FOR')
        target = self._parse_for_target()
        self._expect('IN')
        iterable = self._parse_expression()
        self._expect('COLON')
        body = self._parse_block()
        else_body = []
        self._skip_newlines_raw()
        if self._check('ELSE'):
            self._advance()
            self._expect('COLON')
            else_body = self._parse_block()
        return ForStatement(target, iterable, body, else_body, line=line)

    def _parse_for_target(self):
        """for x, y in ...  or  for x in ..."""
        targets = [Identifier(self._expect('NAME').value)]
        while self._check('COMMA'):
            self._advance()
            if self._check('NAME'):
                targets.append(Identifier(self._advance().value))
        return targets[0] if len(targets) == 1 else TupleLiteral(targets)

    def _parse_funcdef(self):
        line = self._peek().line
        self._expect('DEF')
        name = self._expect('NAME').value
        self._expect('LPAREN')
        params = self._parse_params()
        self._expect('RPAREN')
        return_type = None
        if self._check('ARROW'):
            self._advance()
            return_type = self._parse_type_hint()
        self._expect('COLON')
        body = self._parse_block()
        return FunctionDef(name, params, body, return_type, line=line)

    def _parse_params(self):
        """Returns list of (name, default, type_hint)."""
        params = []
        if self._check('RPAREN'):
            return params
        while True:
            name = self._expect('NAME').value
            type_hint = None
            default = None
            if self._check('COLON'):
                self._advance()
                type_hint = self._parse_type_hint()
            if self._check('ASSIGN'):
                self._advance()
                default = self._parse_expression()
            params.append((name, default, type_hint))
            if not self._check('COMMA'):
                break
            self._advance()
        return params

    def _parse_classdef(self):
        line = self._peek().line
        self._expect('CLASS')
        name = self._expect('NAME').value
        bases = []
        if self._check('LPAREN'):
            self._advance()
            while not self._check('RPAREN'):
                bases.append(self._expect('NAME').value)
                if self._check('COMMA'):
                    self._advance()
            self._expect('RPAREN')
        self._expect('COLON')
        body = self._parse_block()
        return ClassDef(name, bases, body, line=line)

    def _parse_return(self):
        line = self._peek().line
        self._expect('RETURN')
        value = None
        if not self._check('NEWLINE') and not self._check('EOF') and \
           not (self._raw_pos < len(self._raw_tokens) and
                self._raw_tokens[self._raw_pos].type == 'NEWLINE'):
            value = self._parse_expression()
        self._consume_stmt_end()
        return ReturnStatement(value, line=line)

    def _parse_print(self):
        line = self._peek().line
        self._expect('PRINT')
        # print as statement: print x  OR  print(x, y, sep=',')
        sep = ' '
        end = '\n'
        args = []
        if self._check('LPAREN'):
            self._advance()
            if not self._check('RPAREN'):
                while True:
                    # check for sep= / end= keyword args
                    if self._check('NAME') and self._peek().value in ('sep', 'end'):
                        kw = self._advance().value
                        self._expect('ASSIGN')
                        val = self._parse_expression()
                        if kw == 'sep':
                            sep = val.value if isinstance(val, StringLiteral) else ' '
                        else:
                            end = val.value if isinstance(val, StringLiteral) else '\n'
                    else:
                        args.append(self._parse_expression())
                    if not self._check('COMMA'):
                        break
                    self._advance()
            self._expect('RPAREN')
        else:
            # Python 2-style print (not supported, but graceful)
            args.append(self._parse_expression())
        self._consume_stmt_end()
        return PrintStatement(args, sep=sep, end=end, line=line)

    def _parse_import(self):
        line = self._peek().line
        self._expect('IMPORT')
        module = self._expect('NAME').value
        alias = None
        if self._check('AS'):
            self._advance()
            alias = self._expect('NAME').value
        self._consume_stmt_end()
        return ImportStatement(module, alias, line=line)

    def _parse_from_import(self):
        line = self._peek().line
        self._expect('FROM')
        module = self._expect('NAME').value
        self._expect('IMPORT')
        names = []
        while True:
            n = self._expect('NAME').value
            alias = None
            if self._check('AS'):
                self._advance()
                alias = self._expect('NAME').value
            names.append((n, alias))
            if not self._check('COMMA'):
                break
            self._advance()
        self._consume_stmt_end()
        return FromImport(module, names, line=line)

    def _parse_global(self):
        line = self._peek().line
        self._expect('GLOBAL')
        names = [self._expect('NAME').value]
        while self._check('COMMA'):
            self._advance()
            names.append(self._expect('NAME').value)
        self._consume_stmt_end()
        return GlobalStatement(names, line=line)

    def _parse_del(self):
        line = self._peek().line
        self._expect('DEL')
        target = self._parse_expression()
        self._consume_stmt_end()
        return DeleteStatement(target, line=line)

    def _parse_assert(self):
        line = self._peek().line
        self._expect('ASSERT')
        condition = self._parse_expression()
        msg = None
        if self._check('COMMA'):
            self._advance()
            msg = self._parse_expression()
        self._consume_stmt_end()
        return AssertStatement(condition, msg, line=line)

    def _parse_raise(self):
        line = self._peek().line
        self._expect('RAISE')
        exc = None
        if not self._check('NEWLINE') and not self._check('EOF'):
            exc = self._parse_expression()
        self._consume_stmt_end()
        return RaiseStatement(exc, line=line)

    def _parse_try(self):
        line = self._peek().line
        self._expect('TRY')
        self._expect('COLON')
        body = self._parse_block()
        handlers = []
        self._skip_newlines_raw()
        while self._check('EXCEPT'):
            self._advance()
            exc_type = None
            exc_name = None
            if not self._check('COLON'):
                exc_type = self._expect('NAME').value
                if self._check('AS'):
                    self._advance()
                    exc_name = self._expect('NAME').value
            self._expect('COLON')
            h_body = self._parse_block()
            handlers.append((exc_type, exc_name, h_body))
            self._skip_newlines_raw()
        else_body = []
        finally_body = []
        if self._check('ELSE'):
            self._advance()
            self._expect('COLON')
            else_body = self._parse_block()
            self._skip_newlines_raw()
        if self._check('FINALLY'):
            self._advance()
            self._expect('COLON')
            finally_body = self._parse_block()
        return TryStatement(body, handlers, else_body, finally_body, line=line)

    def _parse_with(self):
        line = self._peek().line
        self._expect('WITH')
        expr = self._parse_expression()
        target = None
        if self._check('AS'):
            self._advance()
            target = Identifier(self._expect('NAME').value)
        self._expect('COLON')
        body = self._parse_block()
        return WithStatement(expr, target, body, line=line)

    def _parse_match(self):
        line = self._peek().line
        self._expect('MATCH')
        subject = self._parse_expression()
        self._expect('COLON')
        cases = []
        self._skip_newlines_raw()
        if self._raw_pos < len(self._raw_tokens) and \
           self._raw_tokens[self._raw_pos].type == 'INDENT':
            self._raw_pos += 1
        while True:
            self._skip_newlines_raw()
            if not self._check('CASE'):
                break
            self._advance()  # consume 'case'
            pattern = self._parse_match_pattern()
            guard = None
            if self._check('IF'):
                self._advance()
                guard = self._parse_expression()
            self._expect('COLON')
            body = self._parse_block()
            cases.append((pattern, guard, body))
        self._skip_newlines_raw()
        if self._raw_pos < len(self._raw_tokens) and \
           self._raw_tokens[self._raw_pos].type == 'DEDENT':
            self._raw_pos += 1
        return MatchStatement(subject, cases, line=line)

    def _parse_match_pattern(self):
        """Simplified pattern: literal, name, or wildcard _"""
        tok = self._peek()
        if tok.type in ('INT', 'FLOAT', 'STRING', 'TRUE', 'FALSE', 'NONE'):
            self._advance()
            if tok.type == 'INT':   return NumberLiteral(tok.value, tok.line)
            if tok.type == 'FLOAT': return NumberLiteral(tok.value, tok.line)
            if tok.type == 'STRING': return StringLiteral(tok.value, tok.line)
            if tok.type == 'TRUE':  return BoolLiteral(True, tok.line)
            if tok.type == 'FALSE': return BoolLiteral(False, tok.line)
            if tok.type == 'NONE':  return NoneLiteral(tok.line)
        if tok.type == 'NAME':
            self._advance()
            return Identifier(tok.value, tok.line)
        return self._parse_expression()

    # ─── expressions (Pratt / recursive descent) ─────────────────────────────

    def _parse_expression(self):
        """Entry point for expressions (handles ternary, lambda)."""
        if self._check('LAMBDA'):
            return self._parse_lambda()
        expr = self._parse_or()
        # ternary: x if cond else y
        if self._check('IF'):
            self._advance()
            condition = self._parse_or()
            self._expect('ELSE')
            false_val = self._parse_expression()
            return TernaryOp(condition, expr, false_val, line=expr.line)
        # walrus :=
        if self._check('WALRUS'):
            self._advance()
            value = self._parse_expression()
            if isinstance(expr, Identifier):
                return Assignment(expr, value, line=expr.line)
        return expr

    def _parse_lambda(self):
        line = self._peek().line
        self._expect('LAMBDA')
        params = []
        if not self._check('COLON'):
            params.append(self._expect('NAME').value)
            while self._check('COMMA'):
                self._advance()
                params.append(self._expect('NAME').value)
        self._expect('COLON')
        body = self._parse_expression()
        return LambdaExpr(params, body, line=line)

    def _parse_or(self):
        left = self._parse_and()
        while self._check('OR'):
            self._advance()
            right = self._parse_and()
            if isinstance(left, BoolOp) and left.op == 'or':
                left.values.append(right)
            else:
                left = BoolOp('or', [left, right], line=left.line)
        return left

    def _parse_and(self):
        left = self._parse_not()
        while self._check('AND'):
            self._advance()
            right = self._parse_not()
            if isinstance(left, BoolOp) and left.op == 'and':
                left.values.append(right)
            else:
                left = BoolOp('and', [left, right], line=left.line)
        return left

    def _parse_not(self):
        if self._check('NOT'):
            line = self._peek().line
            self._advance()
            operand = self._parse_not()
            return UnaryOp('not', operand, line=line)
        return self._parse_comparison()

    def _parse_comparison(self):
        left = self._parse_bitor()
        ops = []
        comparators = []
        CMP = {'LT': '<', 'GT': '>', 'LE': '<=', 'GE': '>=', 'EQ': '==', 'NE': '!='}
        while True:
            t = self._peek()
            if t.type in CMP:
                ops.append(CMP[t.type])
                self._advance()
                comparators.append(self._parse_bitor())
            elif t.type == 'IN':
                ops.append('in')
                self._advance()
                comparators.append(self._parse_bitor())
            elif t.type == 'NOT' and self._peek(1).type == 'IN':
                ops.append('not in')
                self._advance(); self._advance()
                comparators.append(self._parse_bitor())
            elif t.type == 'IS':
                self._advance()
                if self._check('NOT'):
                    self._advance()
                    ops.append('is not')
                else:
                    ops.append('is')
                comparators.append(self._parse_bitor())
            else:
                break
        if not ops:
            return left
        if len(ops) == 1:
            op = ops[0]
            right = comparators[0]
            if op in ('in', 'not in'):
                return InOperator(left, right, negated=(op == 'not in'), line=left.line)
            if op in ('is', 'is not'):
                return IsOperator(left, right, negated=(op == 'is not'), line=left.line)
            return CompareOp(left, ops, comparators, line=left.line)
        return CompareOp(left, ops, comparators, line=left.line)

    def _parse_bitor(self):
        left = self._parse_bitxor()
        while self._check('PIPE'):
            self._advance()
            left = BinaryOp(left, '|', self._parse_bitxor(), line=left.line)
        return left

    def _parse_bitxor(self):
        left = self._parse_bitand()
        while self._check('CARET'):
            self._advance()
            left = BinaryOp(left, '^', self._parse_bitand(), line=left.line)
        return left

    def _parse_bitand(self):
        left = self._parse_shift()
        while self._check('AMPERSAND'):
            self._advance()
            left = BinaryOp(left, '&', self._parse_shift(), line=left.line)
        return left

    def _parse_shift(self):
        left = self._parse_add()
        while self._check('LSHIFT', 'RSHIFT'):
            op = self._advance().type
            left = BinaryOp(left, '<<' if op == 'LSHIFT' else '>>', self._parse_add(), line=left.line)
        return left

    def _parse_add(self):
        left = self._parse_mul()
        while self._check('PLUS', 'MINUS'):
            op = self._advance().value
            left = BinaryOp(left, op, self._parse_mul(), line=left.line)
        return left

    def _parse_mul(self):
        left = self._parse_unary()
        while self._check('STAR', 'SLASH', 'PERCENT', 'FLOOR_DIV'):
            t = self._advance()
            op = {'STAR': '*', 'SLASH': '/', 'PERCENT': '%', 'FLOOR_DIV': '//'}[t.type]
            left = BinaryOp(left, op, self._parse_unary(), line=left.line)
        return left

    def _parse_unary(self):
        t = self._peek()
        if t.type in ('MINUS', 'PLUS', 'TILDE'):
            self._advance()
            op = {'-': '-', '+': '+', '~': '~'}[t.value]
            return UnaryOp(op, self._parse_unary(), line=t.line)
        return self._parse_power()

    def _parse_power(self):
        base = self._parse_postfix()
        if self._check('POWER'):
            self._advance()
            exp = self._parse_unary()  # right-associative
            return BinaryOp(base, '**', exp, line=base.line)
        return base

    def _parse_postfix(self):
        """Handle attribute access, index/slice, function calls."""
        node = self._parse_primary()
        while True:
            if self._check('DOT'):
                self._advance()
                attr = self._expect('NAME').value
                if self._check('LPAREN'):
                    self._advance()
                    args, kwargs = self._parse_call_args()
                    self._expect('RPAREN')
                    node = FunctionCall(AttributeAccess(node, attr, line=node.line), args, kwargs, line=node.line)
                else:
                    node = AttributeAccess(node, attr, line=node.line)
            elif self._check('LBRACKET'):
                self._advance()
                node = self._parse_subscript(node)
                self._expect('RBRACKET')
            elif self._check('LPAREN'):
                self._advance()
                args, kwargs = self._parse_call_args()
                self._expect('RPAREN')
                node = FunctionCall(node, args, kwargs, line=node.line)
            else:
                break
        return node

    def _parse_subscript(self, obj):
        """obj[start:stop:step] or obj[index]"""
        # check for slice
        start = None
        stop = None
        step = None
        if not self._check('COLON') and not self._check('RBRACKET'):
            start = self._parse_expression()
        if self._check('COLON'):
            self._advance()
            if not self._check('COLON') and not self._check('RBRACKET'):
                stop = self._parse_expression()
            if self._check('COLON'):
                self._advance()
                if not self._check('RBRACKET'):
                    step = self._parse_expression()
            return SliceAccess(obj, start, stop, step, line=obj.line)
        return IndexAccess(obj, start, line=obj.line)

    def _parse_call_args(self):
        args = []
        kwargs = {}
        if self._check('RPAREN'):
            return args, kwargs
        while True:
            if self._check('NAME') and self._peek(1).type == 'ASSIGN':
                kw = self._advance().value
                self._advance()  # '='
                kwargs[kw] = self._parse_expression()
            else:
                args.append(self._parse_expression())
            if not self._check('COMMA'):
                break
            self._advance()
            if self._check('RPAREN'):
                break
        return args, kwargs

    def _parse_primary(self):
        tok = self._peek()
        t = tok.type

        # literals
        if t == 'INT':
            self._advance()
            return NumberLiteral(tok.value, tok.line)
        if t == 'FLOAT':
            self._advance()
            return NumberLiteral(tok.value, tok.line)
        if t == 'STRING':
            self._advance()
            return StringLiteral(tok.value, tok.line)
        if t == 'TRUE':
            self._advance()
            return BoolLiteral(True, tok.line)
        if t == 'FALSE':
            self._advance()
            return BoolLiteral(False, tok.line)
        if t == 'NONE':
            self._advance()
            return NoneLiteral(tok.line)

        # identifier
        if t == 'NAME':
            self._advance()
            return Identifier(tok.value, tok.line)

        # print used as expression (e.g., passed as argument)
        if t == 'PRINT':
            self._advance()
            return Identifier('print', tok.line)

        # parenthesized expression or tuple
        if t == 'LPAREN':
            self._advance()
            if self._check('RPAREN'):
                self._advance()
                return TupleLiteral([], tok.line)
            expr = self._parse_expression()
            if self._check('COMMA'):
                # tuple
                elements = [expr]
                while self._check('COMMA'):
                    self._advance()
                    if self._check('RPAREN'):
                        break
                    elements.append(self._parse_expression())
                self._expect('RPAREN')
                return TupleLiteral(elements, tok.line)
            self._expect('RPAREN')
            return expr

        # list or list comprehension
        if t == 'LBRACKET':
            return self._parse_list_or_comp(tok)

        # dict or set or set/dict comprehension
        if t == 'LBRACE':
            return self._parse_dict_or_set(tok)

        # f-string (simplified as string)
        if t == 'MISMATCH' and tok.value in ('f', 'b', 'r'):
            self._advance()
            if self._check('STRING'):
                s = self._advance()
                return StringLiteral(s.value, tok.line)

        raise ParseError(
            f"Unexpected token {tok.type!r} ({repr(tok.value)})",
            tok.line, tok.col
        )

    def _parse_list_or_comp(self, open_tok):
        self._advance()  # consume '['
        line = open_tok.line
        if self._check('RBRACKET'):
            self._advance()
            return ListLiteral([], line)
        first = self._parse_expression()
        # list comprehension
        if self._check('FOR'):
            self._advance()
            target = self._parse_for_target()
            self._expect('IN')
            iterable = self._parse_expression()
            condition = None
            if self._check('IF'):
                self._advance()
                condition = self._parse_expression()
            self._expect('RBRACKET')
            return ListComp(first, target, iterable, condition, line=line)
        # regular list
        elements = [first]
        while self._check('COMMA'):
            self._advance()
            if self._check('RBRACKET'):
                break
            elements.append(self._parse_expression())
        self._expect('RBRACKET')
        return ListLiteral(elements, line)

    def _parse_dict_or_set(self, open_tok):
        self._advance()  # consume '{'
        line = open_tok.line
        if self._check('RBRACE'):
            self._advance()
            return DictLiteral([], line)  # empty dict
        first = self._parse_expression()
        # dict or dict comprehension
        if self._check('COLON'):
            self._advance()
            first_val = self._parse_expression()
            if self._check('FOR'):
                # dict comprehension
                self._advance()
                target = self._parse_for_target()
                self._expect('IN')
                iterable = self._parse_expression()
                condition = None
                if self._check('IF'):
                    self._advance()
                    condition = self._parse_expression()
                self._expect('RBRACE')
                return DictComp(first, first_val, target, iterable, condition, line=line)
            pairs = [(first, first_val)]
            while self._check('COMMA'):
                self._advance()
                if self._check('RBRACE'):
                    break
                k = self._parse_expression()
                self._expect('COLON')
                v = self._parse_expression()
                pairs.append((k, v))
            self._expect('RBRACE')
            return DictLiteral(pairs, line)
        # set or set comprehension
        if self._check('FOR'):
            self._advance()
            target = self._parse_for_target()
            self._expect('IN')
            iterable = self._parse_expression()
            condition = None
            if self._check('IF'):
                self._advance()
                condition = self._parse_expression()
            self._expect('RBRACE')
            return SetComp(first, target, iterable, condition, line=line)
        elements = [first]
        while self._check('COMMA'):
            self._advance()
            if self._check('RBRACE'):
                break
            elements.append(self._parse_expression())
        self._expect('RBRACE')
        return SetLiteral(elements, line)


# ─── convenience ─────────────────────────────────────────────────────────────

def parse(source: str) -> Program:
    tokens = tokenize(source)
    return Parser(tokens).parse()


if __name__ == '__main__':
    import sys
    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    tree = parse(src)
    def _print_tree(node, indent=0):
        prefix = '  ' * indent
        if isinstance(node, list):
            for n in node: _print_tree(n, indent)
            return
        print(f"{prefix}{repr(node)}")
        for attr in ('statements', 'body', 'else_body', 'elif_clauses'):
            val = getattr(node, attr, None)
            if val:
                if attr == 'elif_clauses':
                    for cond, b in val:
                        print(f"{prefix}  elif {repr(cond)}:")
                        _print_tree(b, indent+2)
                else:
                    _print_tree(val, indent+1)
    _print_tree(tree)
