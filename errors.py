"""
errors.py - Custom error classes for the Mini Python Compiler
"""


class CompilerError(Exception):
    """Base class for all compiler errors."""
    def __init__(self, message, line=None, col=None, error_type="Error"):
        self.message = message
        self.line = line
        self.col = col
        self.error_type = error_type
        loc = f" (line {line}" + (f", col {col}" if col else "") + ")" if line else ""
        super().__init__(f"{error_type}{loc}: {message}")


class LexerError(CompilerError):
    def __init__(self, message, line=None, col=None):
        super().__init__(message, line, col, "LexerError")


class ParseError(CompilerError):
    def __init__(self, message, line=None, col=None):
        super().__init__(message, line, col, "ParseError")


class SemanticError(CompilerError):
    def __init__(self, message, line=None, col=None):
        super().__init__(message, line, col, "SemanticError")


class RuntimeError_(CompilerError):
    def __init__(self, message, line=None, col=None):
        super().__init__(message, line, col, "RuntimeError")


class BreakSignal(Exception):
    """Internal signal for break statement."""
    pass


class ContinueSignal(Exception):
    """Internal signal for continue statement."""
    pass


class ReturnSignal(Exception):
    """Internal signal for return statement."""
    def __init__(self, value):
        self.value = value
