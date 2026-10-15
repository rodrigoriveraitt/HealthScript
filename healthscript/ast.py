from dataclasses import dataclass, field
from typing import List, Union


@dataclass
class Node:
    line: int
    column: int


@dataclass
class Literal(Node):
    value: Union[float, str, bool, None]


@dataclass
class Variable(Node):
    name: str


@dataclass
class UnaryOp(Node):
    operator: str
    operand: Node


@dataclass
class BinaryOp(Node):
    left: Node
    operator: str
    right: Node


@dataclass
class Assignment(Node):
    name: str
    expression: Node


@dataclass
class Action(Node):
    kind: str
    message: Union[str, None] = None
    assignment: Union[Assignment, None] = None


@dataclass
class Rule(Node):
    name: Union[str, None]
    condition: Node
    actions: List[Action] = field(default_factory=list)


@dataclass
class Program(Node):
    patient_id: Union[str, None] = None
    statements: List[Union[Assignment, Rule]] = field(default_factory=list)


def _expr_text(node: Node) -> str:
    if isinstance(node, Literal):
        if isinstance(node.value, str):
            return f'"{node.value}"'
        if node.value is True:
            return 'VERDADERO'
        if node.value is False:
            return 'FALSO'
        return str(node.value)
    if isinstance(node, Variable):
        return node.name
    if isinstance(node, UnaryOp):
        return f'({node.operator} {_expr_text(node.operand)})'
    if isinstance(node, BinaryOp):
        return f'({_expr_text(node.left)} {node.operator} {_expr_text(node.right)})'
    return '?'


def _render(node: Node, prefix: str, last: bool, lines: list[str]) -> None:
    branch = '└── ' if last else '├── '

    if isinstance(node, Program):
        label = 'Programa'
        if node.patient_id:
            label += f'  [Paciente: {node.patient_id}]'
        lines.append(prefix + branch + label)
        child_prefix = prefix + ('    ' if last else '│   ')
        for i, statement in enumerate(node.statements):
            _render(statement, child_prefix, i == len(node.statements) - 1, lines)
    elif isinstance(node, Assignment):
        lines.append(prefix + branch + f'Asignación: {node.name} =')
        _render(node.expression, prefix + ('    ' if last else '│   '), True, lines)
    elif isinstance(node, Rule):
        name = f' "{node.name}"' if node.name else ''
        lines.append(prefix + branch + f'Regla{name}')
        child_prefix = prefix + ('    ' if last else '│   ')
        lines.append(child_prefix + '├── Condición: ' + _expr_text(node.condition))
        for i, action in enumerate(node.actions):
            is_last = i == len(node.actions) - 1
            if action.kind in ('ALERTA', 'RECOMENDAR'):
                text = f'{action.kind}: "{action.message}"'
            else:
                text = f'Acción: {action.assignment.name} = {_expr_text(action.assignment.expression)}'
            lines.append(child_prefix + ('└── ' if is_last else '├── ') + text)
    elif isinstance(node, Literal):
        lines.append(prefix + branch + 'Literal: ' + _expr_text(node))
    elif isinstance(node, Variable):
        lines.append(prefix + branch + 'Variable: ' + node.name)
    elif isinstance(node, UnaryOp):
        lines.append(prefix + branch + f'Operador unario: {node.operator}')
        _render(node.operand, prefix + ('    ' if last else '│   '), True, lines)
    elif isinstance(node, BinaryOp):
        lines.append(prefix + branch + f'Operador: {node.operator}')
        child_prefix = prefix + ('    ' if last else '│   ')
        _render(node.left, child_prefix, False, lines)
        _render(node.right, child_prefix, True, lines)


def ast_to_text(program: Program) -> str:
    lines: list[str] = []
    _render(program, '', True, lines)
    return '\n'.join(lines)
