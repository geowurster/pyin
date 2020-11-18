import os
import traceback


class CLIError(Exception):

    """Raised by the commandline interface. Used to catch, reformat, and print
    specific exceptions in a manner that is more user friendly.
    """


class CompileError(Exception):

    """Indicates that something did not compile correctly. See the
    ``from_syntax_error()`` method for a special case.
    """

    @classmethod
    def from_syntax_error(cls, syntax_error):

        """Python has special ``SyntaxError`` that is reconstructed here.

        Parameters
        ==========
        syntax_error : SyntaxError
        """

        if not isinstance(syntax_error, SyntaxError):
            raise TypeError(
                "did not receive a {} - instead found a {} with message:"
                " {}".format(
                    SyntaxError.__name__,
                    syntax_error.__class__.__name__,
                    str(syntax_error)))

        lines = traceback.format_exception_only(
            syntax_error.__class__, syntax_error)
        lines = [l.rstrip() for l in lines]
        lines[0] = "failed to compile code:"

        return cls(os.linesep.join(lines))


class EvaluateError(Exception):

    """Raised when an expression could not be evaluated."""
