from dataclasses import dataclass
import re


class LexicalError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    column: int

    def display(self) -> str:
        return f'{self.type:<12} {self.value!r:<28} línea {self.line}, col {self.column}'


KEYWORDS = {
    'PACIENTE', 'SI', 'ENTONCES', 'FIN', 'ALERTA', 'RECOMENDAR',
    'REGLA', 'Y', 'O', 'VERDADERO', 'FALSO'
}

TOKEN_SPEC = [
    ('NUMBER',   r'\d+(?:\.\d+)?'),
    ('STRING',   r'"(?:\\.|[^"\\])*"'),
    ('OP',       r'==|!=|>=|<=|[+\-*/><=()]'),
    ('IDENT',    r'[A-Za-z_][A-Za-z0-9_]*'),
    ('COMMENT',  r'\#[^\n]*'),
    ('SPACE',    r'[ \t\r]+'),
    ('NEWLINE',  r'\n'),
]
TOKEN_RE = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC))


def lex(source: str) -> list[Token]:
    tokens: list[Token] = []
    line = 1
    column = 1
    pos = 0
    length = len(source)

    while pos < length:
        match = TOKEN_RE.match(source, pos)
        if not match:
            char = source[pos]
            raise LexicalError(f'Carácter no reconocido: {char!r}', line, column)

        kind = match.lastgroup
        value = match.group()

        if kind == 'NEWLINE':
            tokens.append(Token('NEWLINE', '\\n', line, column))
            line += 1
            column = 1
        else:
            if kind in ('SPACE', 'COMMENT'):
                pass
            elif kind == 'IDENT':
                token_type = value if value in KEYWORDS else 'IDENT'
                tokens.append(Token(token_type, value, line, column))
            elif kind == 'STRING':
                tokens.append(Token('STRING', value[1:-1].replace('\\"', '"').replace('\\n', '\n'), line, column))
            else:
                tokens.append(Token(kind, value, line, column))
            column += len(value)

        pos = match.end()

    tokens.append(Token('EOF', '', line, column))
    return tokens
