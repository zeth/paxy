# docs/_ext/paxy_lexer.py
from pygments.lexer import RegexLexer, bygroups
from pygments.token import (
    Text,
    Comment,
    Keyword,
    Name,
    Number,
    String,
    Operator,
    Punctuation,
    Whitespace,
)

COMMANDS = r"(LET|PRINT|INPUT|IF|GOTO|LABEL|SUB|SUBEND|RET|GOS|RANGE|RANGEEND|PAR|INC|DEC|MAP|MAD|MAL|ROW|VEC|IGL|ISBOP|INOP|COMPARE|IMPORT)"


class PaxyLexer(RegexLexer):
    """
    Very small lexer for Paxy examples:
    - Treats leading words like LET/PRINT/etc. as keywords
    - Supports # comments to end of line
    - Numbers, strings, names, common operators
    """

    name = "Paxy"
    aliases = ["paxy", "basic"]  # accept both tags
    filenames = []

    tokens = {
        "root": [
            (r"#.*?$", Comment.Single),
            (r"\s+", Whitespace),
            # strings: "..."
            (r'"([^"\\]|\\.)*"', String.Double),
            # numbers: ints and floats
            (r"\b\d+\.\d+\b", Number.Float),
            (r"\b\d+\b", Number.Integer),
            # punctuation (brackets, commas)
            (r"[\[\]\(\),]", Punctuation),
            # operators
            (
                r"(\*\*|//|<<|>>|==|!=|<=|>=|is not|not in|in|is|[+\-*/%&|^<>])",
                Operator.Word,
            ),
            # command keyword at start of line
            (rf"^{COMMANDS}\b", Keyword, "rest_of_line"),
            # otherwise treat bare names
            (r"[A-Za-z_][A-Za-z_0-9]*", Name),
            (r".", Text),
        ],
        "rest_of_line": [
            (r"\s+", Whitespace),
            (r"#.*?$", Comment.Single, "#pop"),
            (r'"([^"\\]|\\.)*"', String.Double),
            (r"\b\d+\.\d+\b", Number.Float),
            (r"\b\d+\b", Number.Integer),
            (r"[\[\]\(\),]", Punctuation),
            (
                r"(\*\*|//|<<|>>|==|!=|<=|>=|is not|not in|in|is|[+\-*/%&|^<>])",
                Operator.Word,
            ),
            (r"[A-Za-z_][A-Za-z_0-9]*", Name),
            (r".", Text),
        ],
    }
