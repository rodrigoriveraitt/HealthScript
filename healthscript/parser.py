from dataclasses import dataclass
from typing import Optional
from .ast import Action, Assignment, BinaryOp, Literal, Program, Rule, UnaryOp, Variable
from .lexer import Token


class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        super().__init__(message)
        self.message = message
        self.line = token.line
        self.column = token.column
        self.token = token


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.i]

    def advance(self) -> Token:
        token = self.current
        if self.i < len(self.tokens) - 1:
            self.i += 1
        return token

    def match(self, *types: str) -> Optional[Token]:
        if self.current.type in types:
            return self.advance()
        return None

    def expect(self, token_type: str, message: str) -> Token:
        if self.current.type != token_type:
            raise ParseError(message, self.current)
        return self.advance()

    def skip_newlines(self) -> None:
        while self.match('NEWLINE'):
            pass

    def parse(self) -> Program:
        program = Program(line=1, column=1)
        self.skip_newlines()
        while self.current.type != 'EOF':
            if self.current.type == 'PACIENTE':
                self.advance()
                token = self.expect('STRING', 'Se esperaba el identificador del paciente entre comillas.')
                program.patient_id = token.value
                self.consume_statement_end()
            elif self.current.type == 'REGLA':
                program.statements.append(self.parse_rule(named=True))
            elif self.current.type == 'SI':
                program.statements.append(self.parse_rule(named=False))
            elif self.current.type == 'IDENT':
                program.statements.append(self.parse_assignment())
            else:
                raise ParseError('Instrucción no válida en el nivel principal.', self.current)
            self.skip_newlines()
        return program

    def consume_statement_end(self) -> None:
        if self.current.type not in ('NEWLINE', 'EOF'):
            raise ParseError('Se esperaba fin de línea.', self.current)
        self.skip_newlines()

    def parse_assignment(self) -> Assignment:
        name = self.expect('IDENT', 'Se esperaba un identificador.').value
        start = self.tokens[self.i - 1]
        self.expect('OP', 'Se esperaba el operador = en la asignación.')
        previous = self.tokens[self.i - 1]
        if previous.value != '=':
            raise ParseError('Se esperaba el operador = en la asignación.', previous)
        expression = self.parse_expression()
        self.consume_statement_end()
        return Assignment(name=name, expression=expression, line=start.line, column=start.column)

    def parse_rule(self, named: bool) -> Rule:
        first = self.advance()  # REGLA o SI
        name = None
        if named:
            name_token = self.expect('STRING', 'Se esperaba el nombre de la regla entre comillas.')
            name = name_token.value
            self.consume_statement_end()
            self.expect('SI', 'Se esperaba SI después del nombre de la regla.')
        # Para reglas sin nombre, SI ya fue consumido en first.
        condition = self.parse_expression()
        self.expect('ENTONCES', 'Se esperaba la palabra reservada ENTONCES después de la condición.')
        self.consume_statement_end()

        actions: list[Action] = []
        while self.current.type not in ('FIN', 'EOF'):
            if self.current.type == 'NEWLINE':
                self.advance()
                continue
            actions.append(self.parse_action())

        self.expect('FIN', 'Se esperaba FIN para cerrar la regla.')
        self.consume_statement_end()
        return Rule(name=name, condition=condition, actions=actions, line=first.line, column=first.column)

    def parse_action(self) -> Action:
        token = self.current
        if token.type in ('ALERTA', 'RECOMENDAR'):
            kind = self.advance().type
            message = self.expect('STRING', f'Se esperaba un mensaje entre comillas después de {kind}.').value
            self.consume_statement_end()
            return Action(kind=kind, message=message, line=token.line, column=token.column)
        if token.type == 'IDENT':
            assignment = self.parse_assignment()
            return Action(kind='ASIGNACION', assignment=assignment, line=token.line, column=token.column)
        raise ParseError('Acción no válida. Se esperaba ALERTA, RECOMENDAR o una asignación.', token)

    # Pratt parser for expressions.
    PRECEDENCE = {
        'O': 1,
        'Y': 2,
        '==': 3, '!=': 3, '>': 3, '<': 3, '>=': 3, '<=': 3,
        '+': 4, '-': 4,
        '*': 5, '/': 5,
    }

    def parse_expression(self, min_precedence: int = 0):
        left = self.parse_unary()
        while True:
            token = self.current
            op = token.value if token.type == 'OP' else token.type if token.type in ('Y', 'O') else None
            if op is None or op not in self.PRECEDENCE:
                break
            precedence = self.PRECEDENCE[op]
            if precedence < min_precedence:
                break
            self.advance()
            right = self.parse_expression(precedence + 1)
            left = BinaryOp(left=left, operator=op, right=right, line=token.line, column=token.column)
        return left

    def parse_unary(self):
        token = self.current
        if token.type == 'OP' and token.value in ('+', '-'):
            self.advance()
            operand = self.parse_unary()
            return UnaryOp(operator=token.value, operand=operand, line=token.line, column=token.column)
        if token.type == 'OP' and token.value == '(':
            self.advance()
            expr = self.parse_expression()
            self.expect('OP', 'Se esperaba ) para cerrar la expresión.')
            previous = self.tokens[self.i - 1]
            if previous.value != ')':
                raise ParseError('Se esperaba ) para cerrar la expresión.', previous)
            return expr
        if token.type == 'NUMBER':
            self.advance()
            value = float(token.value) if '.' in token.value else int(token.value)
            return Literal(value=value, line=token.line, column=token.column)
        if token.type == 'STRING':
            self.advance()
            return Literal(value=token.value, line=token.line, column=token.column)
        if token.type in ('VERDADERO', 'FALSO'):
            self.advance()
            return Literal(value=token.type == 'VERDADERO', line=token.line, column=token.column)
        if token.type == 'IDENT':
            self.advance()
            return Variable(name=token.value, line=token.line, column=token.column)
        raise ParseError('Se esperaba una expresión válida.', token)


def parse(tokens: list[Token]) -> Program:
    return Parser(tokens).parse()
