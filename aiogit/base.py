# coding: utf8
"""
contains common exceptions and values.
"""

__all__ = ('AiogitException', 'AiogitFileExistsError', 'AiogitGitError',
           'AiogitParsingError')


class AiogitException(Exception):
    """
    Base exception for exceptions raised by aiogit
    """
    pass


class AiogitFileExistsError(AiogitException, FileExistsError):
    """
    Raised when a file or directory exists, but must not.
    """
    pass


class AiogitGitError(AiogitException, OSError):
    """
    Raised when a git command returned an error.
    """
    pass


class AiogitParsingError(AiogitException, ValueError):
    """
    Raised when a parsing failed (such as the return of a git command or a diff
    file).
    """
    pass
